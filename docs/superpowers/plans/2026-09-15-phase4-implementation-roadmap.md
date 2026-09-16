# Phase 4 分阶段实施总计划

**Status:** 2026-09-15，P4-P 已人工评审、实现并完成本地验收；其余四批未执行。

**Goal:** 按五个有依赖关系的批次实现真实 Coding Agent / MCP 的评测、诊断和改进验证，不把文档完成视为阶段实现完成。

**Architecture:** 复用 Trace Core 与已有 adapters；评测、诊断和 benchmark runner 分层。统一 Task/Trial、证据引用、四态结果与报告，最小实验层只复用前面阶段的执行与评测接口。

**Tech Stack:** Python 3.11+、Pydantic v2、Protocol、Typer/Rich、pytest、ruff、mypy；真实 Agent、MCP 与隔离环境必须按执行时的授权和版本配置使用。

**Canonical Spec:** [Phase 4 正式规格](../../specs/evaluation-diagnosis-engine.md)。本计划是导航与执行门禁，不重新定义需求或替代各批计划。

## 1. 文档结构与状态

| 文档层 | 职责 |
|---|---|
| 正式规格 | 需求、数据合同、行为、非目标、验收，是唯一事实来源 |
| 阶段设计 | 数据流、模块边界、接口约束、关键设计与风险 |
| 阶段实施计划 | 文件清单、Task、失败测试、最小实现、验证命令与预期结果 |
| 阶段技术报告 | 代码和实际验证完成后记录技术选择、实现及真实结果 |
| HANDOFF | 当前进展、入口、依赖和阻塞，不替代上述文档 |

计划文件允许列出将来要创建的报告路径，但 `docs/reports/` 不提前创建占位文件，不保存规格交付记录。所有计划里的 Expected 均为预期，不能写进报告作为实际结果。

## 2. 五个批次的文档入口

| 顺序 | 批次 | 设计 | 实施计划 | 当前状态 |
|---|---|---|---|---|
| 1 | P4-P：证据就绪与迁移 | [设计](../specs/2026-09-15-phase4-evidence-readiness-design.md) | [计划](2026-09-15-phase4-evidence-readiness.md) | 已完成本地验收，未提交 |
| 2 | P4-A1：任务与独立验证 | [设计](../specs/2026-09-15-phase4-task-verification-design.md) | [计划](2026-09-15-phase4-task-verification.md) | 依赖 P4-P，未执行 |
| 3 | P4-A2：技能化评测 | [设计](../specs/2026-09-15-phase4-skill-evaluation-design.md) | [计划](2026-09-15-phase4-skill-evaluation.md) | 依赖 P4-A1，未执行 |
| 4 | P4-B1：诊断与校准 | [设计](../specs/2026-09-15-phase4-diagnosis-calibration-design.md) | [计划](2026-09-15-phase4-diagnosis-calibration.md) | 依赖 P4-A2，未执行 |
| 5 | P4-B2：改进实验 | [设计](../specs/2026-09-15-phase4-improvement-experiments-design.md) | [计划](2026-09-15-phase4-improvement-experiments.md) | 依赖 P4-B1，未执行 |

```text
评审正式规格和阶段设计
  → P4-P：证据可靠、legacy 隔离  ∥  按 SOURCE_CATALOG 选定 6 个 instance
  → P4-A1：6 任务真实运行与 verifier
  → P4-A2：24 任务、技能与证据审计
  → P4-B1：48 审核轨迹、诊断基线
  → P4-B2：2 个干预实验与复跑比较
  → Phase 5：复用报告/实验数据构建 view model
```

## 3. 接口所有权与交接

| 能力或资产 | 首次交付 | 后续消费者 |
|---|---|---|
| 源事件关联、部分顺序、capture capabilities | P4-P | A1 runner、A2 过程评测 |
| adapter artifact 引用校验 | P4-P | A2 EvidenceAudit |
| legacy_eval 隔离、新 evaluation 命名空间 | P4-P | A1/A2 正式评测 |
| TaskSpec、TrialRecord、VerifierResult | P4-A1 | A2、B1 校准、B2 实验 |
| EvaluationItem 与 outcomes 四态聚合 | P4-A1 | A2 报告与 B2 指标 |
| Environment、AgentRunner、Verifier、Trial 存储 | P4-A1 | A2 真实任务与 B2 复跑 |
| EvidenceRef、EvidenceIndex、EvalPlan、EvaluationReport | P4-A2 | B1 诊断与 B2 比较 |
| 真实多步 MCP 语义完整验收 | P4-A2 | B1 原因调查 |
| DiagnosisReport、InterventionPlan、校准指标 | P4-B1 | B2 实验与 Phase 5 展示 |
| ExperimentSpec、ComparisonReport、干预证据 | P4-B2 | Phase 5 view model |

后续批次扩展已有模型，不再创建第二套 Task/Trial/四态。接口有变更时，先更新正式规格和相应设计，列出受影响的后续计划并补兼容测试。

## 4. 各批次开始条件

### P4-P

- [x] 评审 EVD-01 至 EVD-05、迁移范围和反例测试。
- [x] 记录工作区原有改动与现有验证基线。
- [x] 确认只修复证据并隔离 legacy，不启动正式评分或真实付费运行。

### P4-A1

- [x] P4-P 技术报告及其实际验证已完成。
- [ ] 固定 Task/Trial/VerifierResult 和结果聚合合同。
- [ ] 选择获准真实 Agent 版本、隔离后端和测试 MCP 资源。
- [x] 按 [`benchmarks/eval-suite/SOURCE_CATALOG.md`](../../../benchmarks/eval-suite/SOURCE_CATALOG.md) 为 6 个任务选定 instance（见 [`sources/a1_selection.json`](../../../benchmarks/eval-suite/sources/a1_selection.json)）。许可已记录；参考方案、隐藏测试隔离和 11.3 审核仍属 P4-A1。

### P4-A2

- [ ] P4-A1 已用真实路径验证，而不仅是 fake runner。
- [ ] 固定 EvidenceRef/报告模型、八个技能和权限合同。
- [ ] 将任务扩到 24 个并冻结分组留出清单。
- [ ] 多步 MCP 的实际 schema 与调用证据可以采集或明确报告缺口。

### P4-B1

- [ ] P4-A2 的引用审计、四态与结果控制样例通过。
- [ ] 准备 48 条审核轨迹；至少 24 条自然真实，至少 16 条分组留出。
- [ ] 用开发集完成数值 rubric、验收阈值与基线收益条件，经审核后冻结。
- [ ] 确认模型访问预算、数据外发范围和审核标签隔离。

### P4-B2

- [ ] P4-B1 达到事先冻结的质量门槛，真实结果已报告。
- [ ] 两个不同改进层级实验的任务、干预、固定因素和指标已预注册。
- [ ] 每实验至少 4 个未调参任务，每配置每任务至少 3 次运行。
- [ ] 获得与实验摘要、外部资源、预算和有效期一致的人工授权。

## 5. 任务与验收覆盖

| 要求 | 实施位置 |
|---|---|
| EVD-01 引用、历史兼容 | P4-P Task 3；A2 Task 1/5 |
| EVD-02 调用身份、配对、去重 | P4-P Task 1/2 |
| EVD-03 源时序与时间 | P4-P Task 4 |
| EVD-04 能力与证据缺口 | P4-P Task 1/4；A2 Task 1/3 |
| EVD-05 MCP 衔接与真实工具链 | P4-P Task 4；A2 Task 4 |
| Task/Trial、执行隔离、独立 verifier | A1 Task 1–5 |
| 6 个首批种子 → 24 个分组任务 | A1 Task 6；A2 Task 6 |
| 四态、技能、固定路由、证据报告 | A1 Task 1；A2 Task 1–5 |
| 诊断、弃判、只读工具与自身 trace | B1 Task 1–4 |
| 48 审核轨迹、留出阈值与三条基线 | B1 Task 5/6 |
| 授权干预、复跑、比较与因果限制 | B2 Task 1–5 |
| legacy CLI 与包迁移 | P4-P Task 5；A2 Task 5 |
| 自动化、真实验收、技术报告 | 每批最后一个 Task |

## 6. 通用执行规则

1. 按任务写失败测试、确认目标失败、最小实现、重跑测试。环境错误不是有效 TDD 失败。
2. 所有命令在各批计划中给出；计划编写不表示命令已经执行。
3. 不用合成 fixture 冒充真实 Agent、真实 MCP 或真实校准结果。
4. 缺少环境、权限、预算、审核数据或门槛未通过时，记录阻塞并停止推进。
5. 每批源码和测试运行相关 pytest、ruff、mypy 与 diff 检查；增加模块同步扩展检查范围。
6. 实际验证完成后才创建中文阶段技术报告，再更新 README、PROJECT_SPEC 和 HANDOFF 的交付状态。
7. 不自动提交、不批量暂存已有用户改动、不自动委派子代理；执行方式和提交需独立授权。
8. 原始敏感数据只留在获准本地目录，分享与提交前执行脱敏检查。

## 7. 报告路径与完成定义

每个阶段报告的文件名已在正式规格第 20.3 节与对应计划末尾规定。P4-P 的 [阶段技术报告](../../reports/phase4-evidence-readiness-technical-report.zh-CN.md) 已按实际结果创建；其余批次未创建报告，不创建规格交付报告。

阶段完成必须同时满足：正式需求已评审、计划步骤真实完成、自动化与真实验收通过、数据与证据可追溯、技术报告记录真实结果。仅完成文档、通过旧测试或已运行部分案例均不足以标记完成。

## 8. 当前交接

P4-P 已完成实现与本地验收，未提交；下一次如获准实施，从 P4-A1 开始。保留已完成的来源收集记录，其余四批的代码/真实任务验收不在本次自动启动。
