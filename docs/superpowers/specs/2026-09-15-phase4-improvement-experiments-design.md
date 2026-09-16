# P4-B2：受控改进实验与复跑比较设计

- 日期：2026-09-15
- 状态：设计初稿，待评审；未实现、未验收。
- 正式规格：[Evaluation / Diagnosis 系统规格](../../specs/evaluation-diagnosis-engine.md)。该文件是需求与验收的唯一事实来源。
- 对应计划：[分阶段实施计划](../plans/2026-09-15-phase4-improvement-experiments.md)。
- 总入口：[Phase 4 总实施计划](../plans/2026-09-15-phase4-implementation-roadmap.md)。

本文记录实现边界和接口设计，不替代正式需求，也不包含会话推理过程。

## 1. 目标与依赖

前置：P4-B1 已验收。覆盖正式规格第 7.2、10.1、12、14–16 节。

复用既有 Task、Trial、runner、verifier、Evaluation 与 Diagnosis，增加最小实验注册、成对复跑和比较。不是新的 Agent 框架，也不实现 Phase 5 可视化。

## 2. 架构

```text
Diagnosis 验证方案 + 人工授权
  → ExperimentSpec 注册并冻结
  → 相同任务上的 baseline / candidate 执行
  → 既有 Trial pipeline 与独立验证
  → 按 task/config/repeat 聚合
  → ComparisonReport + 关联诊断更新
```

- `benchmarks/experiments.py`：实验模型、版本和注册。
- `benchmarks/interventions.py`：改动因素、授权范围和配置差异检查。
- `benchmarks/scheduler.py`：有限并发/顺序调度、重置、取消和检查点。
- `benchmarks/comparison.py`：计数、分母、波动和可比较性。
- `benchmarks/report.py`：JSON 与中文摘要。
- 复用 `benchmarks/execution.py` 与 `storage.py`，禁止复制第二套运行/评分实现。

## 3. 实验合同

ExperimentSpec 包含任务/配置/环境/rubric/verifier 摘要、干预因素、固定因素、预算、重复次数、主要指标、回归要求、无效运行判据、授权记录和冻结时间。

相同任务版本下 baseline 与 candidate 的主要差异只能是声明的干预；模型、工具配置等非目标差异使比较不可用。任务不匹配必须拒绝比较，不能按名称凑对。

授权必须关联实验摘要、外部资源范围、预算和有效期。改变写操作、预算或目标配置后必须重新确认，不把过去一次许可当成永久权限。

## 4. 执行与恢复

每个 task/config/repeat 使用干净状态和独立 Trial。动态系统优先冻结或记录重放，无法冻结时记录成对执行顺序与时间限制。

检查点记录计划项、实际 trial_id 和终态。恢复时仅重试按策略允许的未完成项，并检查副作用；禁止重复执行已经成功的写操作。取消保留已执行记录及未执行计划，不制造成功 Trial。

每次实验至少 4 个未用于调参的任务，每个配置每个任务至少 3 次运行。两个不同改进层级的实验合计覆盖 Coding 与 MCP/组合任务。任务选择、干预和指标在查看留出结果之前冻结。

## 5. 指标与解释

端到端完成率分母为注册并调度的全部 Trial，包括环境启动失败、取消和 unknown。有效运行指标另外提供，并保留原始分子、分母和排除依据。

成本包含比较范围内失败尝试；费用不完整时不输出伪精确单位成本。报告每任务通过次数、所有重复均通过比例、波动和回归，不默认运行独立。

ComparisonReport 保留无效、无收益和负向实验。正向结果必须满足冻结指标，且没有新硬约束违反；不得只展示挑选后的成功任务。

只有有效实验支持原诊断预期时，才新增或更新关联的 intervention_supported 记录，并保留原 hypothesis、证据和实验限制。对照收益不是普遍因果保证。

## 6. CLI 与输出

交付 `experiment show`、`experiment compare`，复用 `bench run` 并增加读取受控实验合同的 `--experiment` 模式。后者仍需要授权检查，不能从普通诊断报告自动启动。

compare 默认只读本地已完成记录；授权缺失不会妨碍只读比较，但会阻止运行。输出拒绝覆盖，路径与内容摘要校验与前面批次保持一致。

## 7. 验收与风险

至少两个不同层级实验，至少一个达到预先定义的正向条件且无新硬约束违反；另一个如实报告结果。无正向证据时阶段保持未通过，不能调整留出任务制造效果。

测试覆盖任务版本不匹配、干预超出授权、预算超限、未知分母、无成功、缺费用、恢复去重、动态状态漂移、负向结果与跨实验来源引用。

输出稳定的 Experiment/Comparison 数据供 Phase 5 使用；不在此阶段加入 Web UI 或为了图表修改 Core。

## 阶段技术报告

本批完成实现与实际验证后，创建 `docs/reports/phase4-improvement-experiments-technical-report.zh-CN.md`，按正式规格第 20.3 节记录技术选择、语法规则、设计模式、实现、真实验证与风险。当前不创建报告或占位文件。
