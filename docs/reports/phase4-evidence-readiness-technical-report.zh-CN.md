# P4-P：证据就绪与旧评测隔离技术报告

- 日期：2026-09-15
- 阶段状态：人工需求评审已通过；P4-P 实现及本地验收完成。
- 正式规格：[Phase 4 评测与诊断系统](../specs/evaluation-diagnosis-engine.md)
- 设计：[P4-P 设计](../superpowers/specs/2026-09-15-phase4-evidence-readiness-design.md)
- 实施计划：[P4-P 计划](../superpowers/plans/2026-09-15-phase4-evidence-readiness.md)
- 提交状态：未执行 Git commit；未启动 P4-A1 或其他后续阶段。

## 1. 阶段目标与实际范围

本批修复 Claude Code/Coding adapter 中影响评测可信度的事件身份、调用配对、引用和时序问题，并隔离旧聊天评测包与命令。

实际交付：

- hooks v2 事件身份与显式源信息，继续读取 v1。
- 基于 session、来源范围、call ID 的调用关联与有依据的去重。
- 同一动作 run 上追加 workflow checks，不再重建动作 span。
- adapter 引用、版本、内容摘要和确定性检查一致性审计。
- 与树分组无关的源顺序查询及真实源时间耗时查询。
- 能力声明、未知状态、MCP 原始身份与返回值保留。
- `legacy_eval` 包、`legacy-eval` 命令和新 `eval` 的迁移提示。
- CLI 输入错误、session 路径边界及已有 trace 输出保护。

未交付：Task/Trial runner、正式 Evaluation/Diagnosis 引擎、MCP schema 验证、完整多步 MCP 评测、基准任务执行或通用 Proxy。P4-A1 的并行来源收集不属于本批实现或验收，相关工作区改动保持原状。

## 2. 技术选择

- 继续复用 Pydantic v2 与现有 Trace Core，不增加框架专用 Core 字段。
- 源事件、能力、关联结果、源位置和审计结果使用明确的数据模型；新增合同拒绝未声明字段。
- 使用独立的调用映射代替单一 pending 变量，不根据工具名猜测配对。
- 使用 SHA-256 绑定 workflow checks 与被检查的动作图及能力声明；摘要不是来源真实性签名。
- 使用显式源序号或带时区的源时间查询先后关系，不采用导入时间或树遍历顺序。
- 保留 JSON 为可序列化数据格式，CLI 只负责显示和入口编排。

实际验证环境为 Windows、Python 3.13.11、pytest 9.0.3。项目声明的最低 Python 版本仍为 3.11；本批未额外执行跨版本矩阵。

## 3. 语法与风格规则

- Python 使用 `from __future__ import annotations`、`X | None` 和明确的返回类型。
- 需要运行时解析的 Pydantic 类型保持运行时 import；纯类型引用放入 TYPE_CHECKING。
- 新增合同使用 `ConfigDict(extra="forbid")`；源序号拒绝布尔值、字符串和负数，不静默强制转换为可信序号。
- 新增与修改的主线文件通过 ruff 检查，行宽为 100；只格式化本批涉及文件，没有全仓库格式化。
- 不访问 BuilderTraceWriter 私有成员；通过公开 writer 构建，再在当前 AgentRun 上追加检查。
- 新事件和文档使用 UTF-8；旧 JSONL 继续支持 UTF-8 BOM。

## 4. 架构与设计模式

架构源文件：[P4-P Mermaid](../diagrams/phase4-evidence-readiness.mmd)。

```text
hooks JSONL
  → CorrelationResult（配对 / 缺失 / 歧义 / 去重）
  → NormalizedCodingEvent + SourcePosition
  → BuilderTraceWriter → 单份 AgentRun
  → 当前图上的 workflow checks
  → EvidenceAudit → CLI Evidence Quality / Workflow Checks
```

主要模式：

- **Core / Adapter 分离**：源身份、Coding 规则和 MCP 识别只在 adapters 中。
- **保守关联**：唯一调用关系不足时保留独立事件和 ambiguous/unpaired 状态。
- **部分顺序**：SourcePosition 支持 before、after、concurrent、unknown；不制造全局时间线。
- **内容绑定与版本化检查**：缓存证据须匹配当前对象、规则和确定性预检结果。
- **非破坏式更新**：refresh_workflow_checks 返回副本，保留历史 artifacts 并追加新版本。
- **遗留隔离**：旧包保留功能原样，只迁移 import 与 CLI 接线；新 evaluation 不再重导出旧 suite。

## 5. 实现要点

### 5.1 源事件与采集身份

`build_hook_event` 生成 `coding_hook_event.v2`。新增 capture_id、source_event_id、source_sequence、call_id、scope_id、observed_at 等字段。

没有源 event ID 时生成本地唯一 ID，不再反复生成 evt_1。legacy sequence 字段继续保留，但缺少显式 source_sequence 时不能用它推断源执行顺序。v1 导入产生稳定的记录定位 ID；它不作为源事件去重依据。

现有 sanitizer 已能保留调用 ID 并脱敏 token 等字段，因此复用其实现，并用测试验证，没有为满足计划文件清单而无意义修改 sanitizer。

### 5.2 调用关联

`correlate_events` 支持同名交错调用、乱序到达、权限事件、不同子任务、重试和缺失终态。相同源 ID 但内容不同产生冲突，不被去重；同一调用 ID 被多次不明确复用时标记歧义。

请求参数归属于请求，返回值归属于终态。缺 ID 不回退到按工具名配对。调用范围不明不能通过合并事件补造上下文。

### 5.3 单次构建与证据审计

converter 只构建一次动作图，然后追加 workflow_check span。语义组显式创建，避免 setdefault 参数求值生成无用 span。

`audit_coding_evidence` 检查：

- Core 结构有效性。
- artifact ID 唯一性及 workflow finding 的引用。
- 当前 schema、规则版本与 subject_digest。
- 缓存结论是否与当前确定性预检相符。

历史规则标为 unknown；悬空引用、重复 ID、对象已变化或篡改结论标为 invalid。审计状态仅说明此范围内的证据完整性，不代表任务成功或来源经过认证。

### 5.4 源顺序、覆盖范围和预检

`source_relation` 不依赖语义树顺序。源序号缺失、范围错误或时序矛盾时不能强行推断。大整数序号不转换为浮点数，避免精度损失。

Core 生成时间明确标为 ingestion。`source_duration_ms` 仅使用有效源起止时间，缺少起止信息、仅有单点观察或区间无效时返回 None。

CaptureCapabilities 的完整性必须有显式 coverage_basis。converter 只接收该覆盖范围声明，不继承未经采集的费用或最终状态可用性。字段是否可用由实际消息和 payload 决定；截断和可能的脱敏损失单独列为 gaps。

workflow checks 使用 v2：

- 缺少完整性依据时，“未观察到验证”输出 unknown，而不是确定失败。
- 跨子任务或不同工作目录的动作不能随意当成恢复或验证。
- 运行中的验证不能被判为已通过，也不能仅因尚无成功结果认定不存在验证。
- 明确相关的后续成功复验可以消除相应恢复 finding，但不等于因果诊断或任务验收。

### 5.5 MCP 与原始结果

明确的 MCP 身份优先于同名内建工具，保留原始工具名、server 名称和 raw_result。没有 schema 时明确 unavailable；提供但未核验的 schema 只标为 unverified。

工具协议错误与业务数据中的 status/exit_code 字段分开处理；错误终态或明确非零 shell 退出码不会被 success 文本覆盖。事件 envelope 不被伪装成工具参数。

完整的 schema 快照归一化和真实多步 MCP 评测仍由 P4-A2 完成。

### 5.6 CLI 与 legacy

- `lumi eval` 只输出迁移提示，退出码为 2，不创建聊天 Agent。
- `lumi legacy-eval` 指向 `lumiagent.legacy_eval`，帮助与运行提示明确弃用及已知限制。
- 新 `lumiagent.evaluation` 是空的新主线命名空间，尚无正式评分功能。
- `trace` 拒绝越出 session 根目录的输入、清晰报告非法 JSONL，并拒绝覆盖已有输出。
- `show --checks` 增加 Evidence Quality，历史 pass 不再被当成当前可信结论；输入文件不被改写。

## 6. 测试过程与兼容调整

新增测试先验证失败，再实现对应行为。实际观察到：事件身份 9 个新增测试失败；关联模块尚未实现导致预期导入失败；证据/源顺序模块缺失导致预期导入失败；legacy 迁移 5 个测试失败。实现复核又补充了跨范围验证、缓存篡改、路径越界、缺 payload 等反例，并在修复后通过。

既有测试保留其覆盖目的，但修正不可靠前提：

- 测试“请求与结果能配对”时提供明确 call_id；缺 ID 的反例独立测试不配对。
- 合成完整工作流显式提供源顺序、相关性和完整性声明。
- 旧 v1 trace 缺证据时的期望从确定 pass/warning 调整为 unknown。
- 没有修改已提交的真实或合成 JSON fixtures，也没有删除相关验证断言来通过测试。

前一轮测试基线为 163 项，本批最终为 225 项，增加 62 个测试项。参数化用例按 pytest 收集数量计数。

## 7. 自动化验证结果

实际执行：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q -p no:cacheprovider --tb=short
python -m ruff check --no-cache src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation src/lumiagent/cli.py tests
python -m mypy --cache-dir=nul src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation
git diff --check
```

| 检查 | 退出码 | 实际结果 |
|---|---|---|
| pytest | 0 | 225 passed，1 warning |
| ruff 主线范围 | 0 | All checks passed |
| mypy 主线范围 | 0 | Success，38 source files |
| 已提交 fixture 的 Core 往返与只读检查 | 0 | 11 个全部通过，输入字节不变 |
| legacy 源码迁移比对 | 0 | 四个模块除 import 命名空间外与原实现一致 |
| Trace Core / 既有 MCP 实现差异检查 | 0 | 两个源码范围均未修改 |
| git diff --check | 0 | 无空白错误 |

pytest 使用已批准的正常临时目录运行；关闭 cacheprovider 避免当前沙箱缓存目录限制。已有 `Unknown config option: asyncio_mode` 警告未修复，不影响本次收集到的测试通过。

本批开始时，扩大的 lint 范围有 14 项问题：CLI 导入格式 1 项、旧 evaluation 包 13 项。CLI 格式已修正，旧包随迁移隔离，不通过删改检查规则隐藏新主线问题。旧评分器的 `Hub_tokens` 等缺陷仍保留，未声称其功能已修复。

## 8. 真实来源 fixture 与 CLI 验证

按 P4-P 计划执行：

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli show tests/adapters/claude_code/fixtures/real_session_sanitized_trace.json --checks
python -m lumiagent.cli legacy-eval --help
python -m lumiagent.cli eval sample_eval
```

结果：

- `show --checks` 退出码 0，正常展示 Semantic Summary、Span Tree、Evidence Quality 和 Workflow Checks。
- 该历史 fixture 没有新的能力声明，旧 workflow pass 显示为 untrusted stored status，当前检查状态为 unknown。
- `legacy-eval --help` 退出码 0，不启动 Agent。
- `eval sample_eval` 退出码 2，提示迁移，不调用旧 Agent。
- 在内存副本上刷新历史 fixture 后，新的当前 artifact 通过审计；旧 artifact 保留，源文件未改变。

真实脱敏 fixture 的 SHA-256 为：

```text
03761c29cb7fb7730a8c06a511a8a13c9a26d53d5aa44cb529ab80987f40314a
```

首次 P4-P 本地验收按计划验证既有真实来源数据，未启动新的 Claude Code 会话或外部服务。随后经用户授权补充了第 10 节的真实 Claude Code 验证；两者均不替代 P4-A1/A2 的正式任务资产和多步 MCP 验收。

## 9. 风险、取舍与后续工作

- 历史缺失的调用身份、时间和完整性不能恢复，unknown 是保留边界，不是转换失败。
- 完整性声明是调用者提供的范围依据，不是对事件来源的密码学认证；普通 hooks 路径不会自动声称 complete。
- JSONL 和单 run 内存处理仍是当前实现范围，不承诺生产级高吞吐采集或大规模分析性能。
- 规则仅做高信心预检，相关成功动作不等于证明根因；正式任务结果、schema 语义和诊断仍在后续阶段。
- legacy 评分器仅完成隔离，已有运行缺陷仍在；不能把它作为 P4-A1 的基础。
- 已保留原有及并行文档、来源收集和 `.gitignore` 改动；未自动暂存或提交文件。

下一步进入 P4-A1 前，先核对本批的公开模型和状态合同，再按已写计划实现 Task/Trial、隔离 runner 和独立 verifier。本批不会自动启动下一阶段。


## 10. 真实 Claude Code 单任务补充验证（2026-09-15）

### 10.1 任务与目的

选用已收集的 SWE-bench Verified `pallets__flask-5014`，对应 `coding_bug_001` 的候选实例。目标为：创建名称为空的 Blueprint 时抛出 ValueError。

固定源码提交：`7ee9ceb71e868944a46e1ff00b506772a53a4f1d`。下载快照 SHA-256：`72dd9d3d9876b2f9043ca8a0671ed0d1cf86ebbd6bac90ef092e8a8dd5ba7d83`。

本次只验证 P4-P 在真实 Claude Code 会话中的采集、调用配对和证据边界。没有建立正式 TaskSpec/Trial runner，也没有将结果记为官方 SWE-bench 分数或 P4-A1 完成。

### 10.2 运行与安全边界

- 本机 Claude Code 版本：2.1.236，使用已安装的 native executable。
- 原始仓库固定副本、Agent 工作区、控制脚本、受保护验收器相互分开，均不在当前 LumiAgent 源码目录内。
- 生效工具清单实际为 Edit、Glob、Grep、Read；MCP servers 清单为空。
- 编辑仅允许独立副本中的 `src/flask/blueprints.py`；shell、网络工具、子 Agent 和其他编辑均不可用。
- 使用显式会话设置、禁用自动记忆/无关 CLAUDE.md 与插件配置；没有使用权限绕过模式。
- PreToolUse 门禁经 5 个自检案例验证。门禁调用实际生产 `hooks.main`，不是另造一份采集格式；自检与真实会话使用不同 session ID。
- 参考代码补丁未读取或提供给 Agent。目标测试补丁仅在独立验证副本中应用。
- 设置客户端 1 美元预算阈值、240 秒超时与最多 12 次获准文件操作。客户端费用估计不等于代理服务的实际账单。
- 这是受限制工具的本地 Windows 探测，不是 OS 级容器安全沙箱。Agent 不能执行修改后的代码；候选补丁经检查后由独立验证脚本执行。

### 10.3 验证器环境与基线

验证使用 Windows / Python 3.13.11，独立虚拟环境安装 Werkzeug 2.3.8、itsdangerous 2.2.0 和 blinker 1.9.0，复用本机的 pytest 等依赖，并保存完整环境清单。

初次准备暴露两项环境问题：

1. Windows 写出的 CRLF 测试补丁无法直接应用到 LF 源文件。重新按原始数据的 LF 写入，未改变测试内容。
2. 2023 年源码调用 pkgutil.get_loader / pkgutil.find_loader，Python 3.13 的弃用警告被上游 `filterwarnings = ["error"]` 当作异常，出现 2 passed / 58 errors。此结果被记为环境失败，不计为任务失败。

为本次兼容探测，仅忽略上述两个明确的 DeprecationWarning，前后使用完全相同配置；未修改业务断言或隐藏测试。有效基线随后得到 **1 failed / 59 passed**，唯一失败为 `test_empty_name_not_allowed`，原实现没有抛出 ValueError。

P4-A1 正式环境应冻结任务适配的 Python 版本和依赖，不直接把本次宿主兼容措施当成官方 harness 配置。

### 10.4 实际结果

| 项目 | 实测结果 |
|---|---|
| Claude 会话 | 1 次真实会话，5 turns，进程退出码 0 |
| 修改文件 | 仅 `src/flask/blueprints.py` |
| 修改内容 | 增加非空名称检查并抛出 ValueError，共 3 行插入 |
| 修改前独立测试 | 1 failed / 59 passed |
| 审核补丁后独立测试 | 60 passed；无失败、错误或跳过 |
| Claude 客户端耗时 | 34.718 秒；外部进程墙钟 35.351 秒 |
| 客户端报送费用 | 0.118336 美元；代理实际账单未独立核验 |
| 真实工具请求 | 4 次：Read、Glob、Read、Edit |
| 标准 hooks 记录 | 7 条；4 个工具 span |
| 调用关联 | 3 对完整调用，1 条 unpaired |
| Core / EvidenceAudit | Core 校验通过，当前证据审计 valid |
| 捕获范围与流程检查 | workflow_coverage=partial；workflow checks=unknown |
| 源时间与序号 | 7 条 hooks 均未提供，未用 observed_at 或导入时间伪造 |

独立测试在 Agent 会话完成后运行，没有作为 Agent 自己的 test_run span 写入 trace，也没有据此将 workflow checks 改成 pass。

### 10.5 真实拒绝路径与状态区别

第一次 Read 使用了允许目录之外的路径，被本次 PreToolUse 门禁拦下，工具并未执行。原生 CLI stream 记录 hook_response 的 exit_code=2；门禁日志也记录了对应 call_id 的拒绝。该操作没有原生 PostToolUse/Failure 记录。

随后 Glob、Read、Edit 正常完成。P4-P 没有把后一个 Read 的结果配给前一个被拒绝的 Read，而是保留首个请求为 unpaired。这验证了按调用 ID 关联和缺证据时保守处理的行为。

当前 hooks-only trace 的 `AgentRun.status` 为 pending，来自未确认工具状态的现有聚合映射；这**不表示真实会话尚未运行，也不表示任务失败**。本例必须分别查看：

- 原生 CLI 完成结果：success。
- 独立任务验收：60 个所选测试通过。
- hooks 采集完整性：partial。
- 流程预检：unknown。

P4-A1 必须继续按 Task/Trial 合同分开记录会话生命周期、任务结果和采集质量，并接入门禁/会话结束等补充来源；不能直接用当前 hooks-only 的 RunStatus 判断任务成败，也不能伪造一个原生 tool_result 来消除 unpaired。

### 10.6 本地证据与离线重放

真实 session ID：`0ca52ac3-6b12-473f-ba53-c90132cc0f6d`。

原始 hooks SHA-256：`3f17546bb95f361a5930c0c55d24636757b56babb7c3ada7bbab55bf7ede90c5`。

本地证据保存在已忽略目录：

```text
.lumiagent/benchmarks/p4p-real-flask-5014-20260915/
  README.md
  events.jsonl
  trace.json
  validation-summary.json
  candidate.patch
  before-compat.xml
  after-compat.xml
  guard-decisions.json
  environment-freeze.txt
  preparation.json
  replay_validate.py
```

这些文件包含实际工具返回、本机路径及验收材料，仅本地保留，不直接提交或挂载给被测 Agent。原始事件在转换前后字节不变。

已执行离线重放：

```powershell
python .lumiagent/benchmarks/p4p-real-flask-5014-20260915/replay_validate.py
```

结果为 PASS：7 个真实事件、3 对完整关联和 1 条 unpaired；Core 与当前证据校验通过，unknown 保持不变。重放不调用模型、不运行 benchmark 源码。

### 10.7 覆盖限制与后续

- 本例没有验证 Agent 的 Bash/test_run 采集，也没有连接 MCP server。
- 观察到原生 Glob 返回包含 truncated / countIsComplete 等字段；本次为未截断结果，不能据此声称所有截断变体已覆盖。
- 本例证明这一固定任务和受控配置下的集成行为，不证明全套 benchmark 能力、诊断准确率或重复运行稳定性。
- 下一步应在 P4-A1 固定环境与独立 verifier 的基础上，再验证 MCP 文件系统等第二条路径，并补充明确来源的拒绝/会话结束记录。
