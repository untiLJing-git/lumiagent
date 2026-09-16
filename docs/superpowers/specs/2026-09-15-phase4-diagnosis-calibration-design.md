# P4-B1：诊断引擎与校准设计

- 日期：2026-09-15
- 状态：设计初稿，待评审；未实现、未验收。
- 正式规格：[Evaluation / Diagnosis 系统规格](../../specs/evaluation-diagnosis-engine.md)。该文件是需求与验收的唯一事实来源。
- 对应计划：[分阶段实施计划](../plans/2026-09-15-phase4-diagnosis-calibration.md)。
- 总入口：[Phase 4 总实施计划](../plans/2026-09-15-phase4-implementation-roadmap.md)。

本文记录实现边界和接口设计，不替代正式需求，也不包含会话推理过程。

## 1. 目标、输入与依赖

前置：P4-A2 已验收。覆盖正式规格第 10、11.6、12.3、15、18.3 节。

输入为任务、EvaluationReport、只读 EvidenceIndex 和可选授权调查结果。输出 DiagnosisReport、可导出的 Core Diagnosis 及独立诊断 AgentRun。不得只按 failure label 套固定建议。

## 2. 架构

```text
EvaluationReport
  → 失败项与证据质量检查
  → DiagnosisEngine（有限预算的调查状态机）
  → 只读 trace/产物工具 + 可选 KnowledgeProvider
  → 假设、反证、备选解释与建议
  → 输出 schema / 引用 / 权限审计
  → DiagnosisReport 或 abstained
```

- `diagnosis/models.py`：诊断项、责任层、原因状态、弃判和干预计划。
- `diagnosis/tools.py`：只读证据工具，不开放任意 shell。
- `diagnosis/providers.py`：模型网关协议和现有 provider 的最小适配。
- `diagnosis/engine.py`：有上限的工具循环、取消、预算和重试。
- `diagnosis/knowledge.py`：可选 KnowledgeProvider 和空实现。
- `diagnosis/report.py`：中文报告与 Core 映射。
- `benchmarks/calibration.py`：审核标签、留出控制、基线运行和指标。

本批不强制迁移旧 ReActEngine，也不引入通用多 Agent 编排。若复用 provider，必须新增接口和异常路径测试。

## 3. 原因与证据合同

区分观察事实、hypothesis 和 intervention_supported。B1 新推断默认 hypothesis；仅导入经过校验的既有实验记录时允许 intervention_supported，不能靠模型自评升级。

每条诊断关联具体 Evaluation 要求，包含位置、责任层、支持证据、反证、备选解释、建议和验证方案。一个任务允许多原因。证据不足时输出 abstained 及缺口，不能构造空 failure_type 的 Core Diagnosis。

责任层覆盖 Agent 决策、上下文、工具/schema、环境、权限、采集和评测器。原始故障类型沿用稳定 taxonomy，责任层是单独字段。

## 4. 模型与工具边界

工具只允许读取被授权 bundle 中的 span、artifact、diff、日志及已批准知识项。模型不得访问参考解或故障注入标签，不得执行工具结果中的指令。

网关接收明确 schema，限制 token/费用/调用次数；解析失败在预算内有限重试，仍失败时返回 diagnosis error 与弃判，不把自然语言任意拼成有效报告。

评测与诊断自 trace 记录工具调用、版本、证据访问和费用，不保存隐藏思维链，不计入被测 Agent 成本。没有已授权的模型配置时，真实诊断验证为阻塞状态；fake provider 只用于单元测试。

## 5. 校准集与审核

至少 48 条轨迹、六种结果类型每类至少 4 条、至少 24 条自然真实执行、至少 16 条按任务分组的留出轨迹。自然/注入样本分别计数。

每条标签记录原始来源、结果、可接受原因集合、证据位置、备选解释、是否应该弃判以及两次独立审核。争议原因不能强行作为唯一标准答案。

校准 runner 给模型的是证据视图，评分器才读取标签。数据加载时校验开发/留出来源关系，并记录每次留出集使用。

## 6. 基线、指标与验收门禁

比较确定性规则、单次 LLM Judge 和技能化诊断三条路径，固定同一输入证据政策与评分表。模型、成本、可见范围和预算分别记录。

本批实施前先用开发集制定 `rubric.v1.json` 和 `acceptance.v1.json`：规定人工评分项、分母、弃判计分、主指标、最低阈值和相对基线收益标准，完成评审并记录摘要后才能读取留出结果。这些文件必须有明确数值和通过条件，不能以“效果良好”验收。

留出集报告至少包含结果混淆表、假通过、失败类别/责任层/位置审核、证据充分性、弃判、建议可操作性和成本。达不到冻结阈值时保留失败结果并停止，不重新挑选样本刷过关。

## 7. 输出与风险

交付 `diagnose` 只读入口、校准命令和实际基线比较。B1 提供可验证建议但不自动执行干预；B2 负责授权后的对照复跑。

LLM 的措辞不能作为事实依据；人工标签也可能有歧义，因此保留备选解释和审核分歧，不以单一错误标签掩盖不确定性。

## 阶段技术报告

本批完成实现与实际验证后，创建 `docs/reports/phase4-diagnosis-calibration-technical-report.zh-CN.md`，按正式规格第 20.3 节记录技术选择、语法规则、设计模式、实现、真实验证与风险。当前不创建报告或占位文件。
