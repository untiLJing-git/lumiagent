# P4-P：证据就绪与旧评测隔离设计

- 日期：2026-09-15
- 状态：2026-09-15 用户人工评审通过；P4-P 已实现并完成本地验收，未提交。
- 正式规格：[Evaluation / Diagnosis 系统规格](../../specs/evaluation-diagnosis-engine.md)。该文件是需求与验收的唯一事实来源。
- 对应计划：[分阶段实施计划](../plans/2026-09-15-phase4-evidence-readiness.md)。
- 总入口：[Phase 4 总实施计划](../plans/2026-09-15-phase4-implementation-roadmap.md)。

本文记录实现边界和接口设计，不替代正式需求，也不包含会话推理过程。

## 1. 目标与范围

修复会影响正式评测的证据关联和时序，并为新 evaluation 包释放入口。覆盖正式规格第 6、14、15、17 节；EVD-05 本批完成原始 MCP 身份与参数/结果保留，完整多步 MCP 评测在 P4-A2 验收。

输入：现有 hooks JSONL、Phase 3 AgentRun 和 workflow artifacts。
输出：引用有效、关联可审核、时间来源明确的 AgentRun，以及 capture capabilities。

不实现 Task runner、正式 Evaluation、Diagnosis、通用 MCP Proxy，也不迁移 McpTraceMapper 到 TraceWriter。

## 2. 数据流与模块边界

```text
hooks → 原始事件及采集身份
  → correlation：调用 ID 配对、去重与歧义标记
  → normalizer：动作语义与源信息
  → converter：只构建一份 run / 稳定 span 身份
  → ordering：基于源信息提供先后关系
  → workflow checks + adapter 引用校验
  → 兼容现有 Core 的 AgentRun
```

- `adapters/claude_code/correlation.py` 管理源调用关联，不放入 Core。
- `adapters/coding/ordering.py` 提供与树分组无关的顺序查询。
- `adapters/coding/evidence.py` 校验 adapter artifacts 引用与采集能力。
- 现有 `converter.py`、`events.py`、`hooks.py`、`normalizer.py`、`validator.py` 复用并修正，不重写整个采集系统。

## 3. 关键设计

### 3.1 身份与关联

关联键为 session、来源子任务范围与源 tool call ID。允许多条 pending 请求并存。请求与结果不能按工具名配对；无唯一关联时保留分离动作并标记 ambiguous。

源事件身份与本地采集身份分开。源系统没有 event_id 或 sequence 时，不继续制造大量 `evt_1`；本地 ID 必须唯一，接收顺序只标记为 ingestion order，不能冒充源执行顺序。只有身份与内容均能证明重复时才去重。

### 3.2 构建与证据

构建动作 run 后，在同一 run 上附加 workflow_check span/artifacts，并再次验证，不重新生成动作 span ID。不通过访问 BuilderTraceWriter 私有字段获得实现捷径。

语义分组按明确的创建条件建立；避免调用 `setdefault` 参数时额外创建未使用的 span。每个源动作只能对应预期的一个动作 span。

历史文件保持不变。历史 findings 引用失效时保留原结果、标记 invalid；需要重算时在当前 run 的副本中计算，并记录规则版本和来源。

### 3.3 顺序与时间

保留 source_event_ids、source sequence、源时间和调用关系。顺序查询返回 before / after / concurrent / unknown；不能比较时检查结果不得假装确定。

首版在 adapter metadata/artifacts 保存源开始和结束时间，并标明 Core 生成时间的 ingestion 来源；不新增 Core 必填字段。只有可靠源时间才能进入效率指标。语义 enrichment 也要保存源位置，无法定位时不强行排列。

### 3.4 兼容合同

旧事件格式继续可读；缺少新增字段时使用明确的 unknown/default，并记录能力缺口。新事件版本与迁移规则需通过往返测试。现有 Core validator 保持框架无关，adapter evidence validator 单独调用。

未知 MCP 工具保留原始 tool_name、server 身份和结果，不把它静默当成 shell 执行；schema 未采集时明确 unavailable。

## 4. Legacy 边界

将原 `evaluation` 四个模块迁至 `legacy_eval`，更新包内引用及 CLI 的惰性 import。新 `evaluation/__init__.py` 仅建立新主线命名空间，不重导出旧 suite。

`legacy-eval` 保留旧入口并提示遗留状态；新 eval 未交付前，`eval` 只提示迁移并非零退出。不得在 help 或输入解析时创建聊天 Agent、初始化 RAG 或访问网络。迁移测试使用替身验证接线，不宣称旧打分器的已知问题已修复。

## 5. 交接合同

P4-A1 接收稳定的 source/capture metadata 和 AgentRun；P4-A2 接收 adapter 引用校验、顺序查询和能力声明。正式评分实现仍在后续阶段。

## 6. 验收与风险

- 同名交错请求 A/B 正确配对，缺 ID 时不误配。
- 转换一次后 finding 引用全部存在；历史悬空引用可发现。
- 测试失败→编辑→测试通过的顺序不被语义分组改写。
- 缺源时间不报告伪执行耗时，部分 trace 不被当成完整证据。
- 现有 fixture 仍可读取；必要的语义期望更新必须明确关联修复，不能删掉失败断言。
- CLI 新旧输入隔离，源码无回指旧 evaluation.suite 的主线 import。

源 ID 缺失和历史时间缺失不能靠转换恢复，必须保留不确定性。完整 MCP schema、真实多步运行属于 P4-A2；本批不能据此宣布完整 MCP 评测已经可用。

## 阶段技术报告

本批完成实现与实际验证后，创建 `docs/reports/phase4-evidence-readiness-technical-report.zh-CN.md`，按正式规格第 20.3 节记录技术选择、语法规则、设计模式、实现、真实验证与风险。现已按实际验证创建 [P4-P 技术报告](../../reports/phase4-evidence-readiness-technical-report.zh-CN.md)，没有使用占位报告。
