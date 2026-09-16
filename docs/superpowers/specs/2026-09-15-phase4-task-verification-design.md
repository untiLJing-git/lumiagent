# P4-A1：任务执行与独立结果验证设计

- 日期：2026-09-15
- 状态：设计初稿，待评审；未实现、未验收。
- 正式规格：[Evaluation / Diagnosis 系统规格](../../specs/evaluation-diagnosis-engine.md)。该文件是需求与验收的唯一事实来源。
- 对应计划：[分阶段实施计划](../plans/2026-09-15-phase4-task-verification.md)。
- 总入口：[Phase 4 总实施计划](../plans/2026-09-15-phase4-implementation-roadmap.md)。

本文记录实现边界和接口设计，不替代正式需求，也不包含会话推理过程。

## 1. 目标、输入与依赖

前置：P4-P 已验收。覆盖正式规格第 4、5、7、8.2、9.1、11.3、13–15 节。

交付任务合同、单次运行、隔离环境、真实 Claude Code runner、独立 verifier 和 6 个种子任务。只实现程序化结果检查；技能路由和完整 eval CLI 留给 P4-A2。

## 2. 架构与模块

```text
suite + AgentConfig
  → TaskSpec 解析、授权与预算检查
  → Environment.prepare / healthcheck
  → AgentRunner.run → AgentRun + 候选产物
  → Verifier.verify → VerifierResult + verifier AgentRun
  → 结果聚合 + TrialRecord + 原子保存
  → Environment.cleanup
```

- `benchmarks/models.py`：TaskSpec、AgentConfig、TrialRecord、VerifierResult。
- `benchmarks/environment.py`：Environment Protocol 和隔离/重置/清理合同。
- `benchmarks/environments/container.py`：首个容器环境实现。
- `benchmarks/runners/base.py` 与 `claude_code.py`：真实 Agent 进程接入。
- `benchmarks/verifier.py` 与 `execution.py`：独立验证与单次运行编排。
- `evaluation/models.py`、`outcomes.py`：单项结果和总体状态；不依赖 LLM。
- `benchmarks/storage.py`：只追加存储、内容摘要与已有输出保护。

## 3. 数据与生命周期

TaskSpec 区分 agent-visible 输入和 verifier-only 材料。requirement_id 唯一，每项有 required、适用条件和 verifier_id。任务内容 version 与 schema_version 分开。

Trial 生命周期为 created → preparing → running → verifying → completed；失败或取消也产生终态记录。运行的执行状态、验证有效性和任务 outcome 分开保存。每次重复分配独立 trial_id 和工作区。

VerifierResult 分开记录 execution_status 和每项检查结果。断言失败是有效 fail；verifier 崩溃对受影响要求产生 unknown。总体状态只按正式规格第 8.2 节聚合，不从 process returncode 直接推断。

P4-A1 输出 trial-index 和稳定的 experiment_id 关联位，不实现比较引擎；P4-B2 在此基础上增加实验注册和比较，不另建第二套 Trial。

## 4. 真实 runner 与隔离

首个 runner 使用 Claude Code 的可配置可执行文件和参数数组。实现时根据获准安装版本验证调用参数并记录版本；不在计划中假定某个 CLI flag 永久有效，也不依赖私有 transcript。

容器实现必须满足工作区隔离、无宿主 Docker socket、无隐藏测试或标签挂载、资源限制和受控网络访问。传入 Agent 的凭证仅限本次允许服务，不写入 trace。临时目录本身不是安全沙箱。

代码候选产物应用到干净验证基线中，验证材料由 evaluator 挂载并限制访问。MCP 写操作限定测试资源，并独立检查最终状态。环境不可用时记录阻塞，不用合成结果代替真实运行。

## 5. 六个首批任务

| ID | 类型 | 验收目的 |
|---|---|---|
| coding_bug_001 | Coding | 从真实问题复现目标失败，并验证修复及回归 |
| coding_interface_001 | Coding | 跨文件接口一致性 |
| mcp_pagination_001 | MCP | 多页读取完整性与终止条件 |
| mcp_update_001 | MCP | 正确对象更新、无重复写入或额外副作用 |
| combined_context_001 | 组合 | 获取 issue/文档上下文后修改并验证 |
| combined_readonly_001 | 组合 | 只读调查有证据且不越权修改 |

这些 ID 属于后续 24 个任务，不重复计数。来源池已锁定并完成 instance 选定，见 [`benchmarks/eval-suite/SOURCE_CATALOG.md`](../../../benchmarks/eval-suite/SOURCE_CATALOG.md) 与 [`benchmarks/eval-suite/sources/a1_selection.json`](../../../benchmarks/eval-suite/sources/a1_selection.json)。构造 `task.json` 时仍须按正式规格 11.3 审核 verifier。

| ID | 锁定主来源 | A1 约束 |
|---|---|---|
| coding_bug_001 | SWE-bench Verified `pallets__flask-5014` | 只抽 1 条；隐藏测试仅 verifier 可见 |
| coding_interface_001 | Multi-SWE-bench mini `mockito__mockito-3129` | 第二仓库（Java）；SWE-Bench Pro 仅作 GPL 指针备选 |
| mcp_pagination_001 | MCP-Universe GitHub issue 枚举形态 + 本地冻结种子 | 不用实时外部 API；种子尚未构造 |
| mcp_update_001 | MCPMark `easy/chinook/update_employee_info` | 不用 GitHub MCP |
| combined_context_001 | Filesystem MCP + SWE-bench Verified `psf__requests-1921` | 不用 GitHub issue API |
| combined_readonly_001 | MCPMark `easy/folder_structure/structure_analysis` 只读改编 | 越权修改为硬约束失败 |

## 6. 安全、异常与存储

启动前验证预算和授权范围；取消、超时及 verifier 失败时仍执行清理。任务产物只在指定 bundle 下保存，防止路径穿越；旧文件拒绝覆盖。

本地 `.lumiagent/benchmarks/`、`.lumiagent/assessments/`、`.lumiagent/config/` 等输出需加入 ignore；目前不能假设整个 `.lumiagent/` 已被忽略。

## 7. 验收与下阶段输出

交付模型、可重复执行 API、`bench run` 最小入口、6 个来源明确的任务和实际运行记录。单元测试使用 fake runner/verifier，真实验收另行执行且明确授权。

输出供 P4-A2 使用的独立 VerifierResult 和只读证据，不提供隐藏答案给诊断器。至少验证通过、有效失败、启动失败、取消、超时和 verifier 异常六类路径。

## 阶段技术报告

本批完成实现与实际验证后，创建 `docs/reports/phase4-task-verification-technical-report.zh-CN.md`，按正式规格第 20.3 节记录技术选择、语法规则、设计模式、实现、真实验证与风险。当前不创建报告或占位文件。
