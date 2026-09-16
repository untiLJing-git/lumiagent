# P4-A2：技能化评测与证据审计设计

- 日期：2026-09-15
- 状态：设计初稿，待评审；未实现、未验收。
- 正式规格：[Evaluation / Diagnosis 系统规格](../../specs/evaluation-diagnosis-engine.md)。该文件是需求与验收的唯一事实来源。
- 对应计划：[分阶段实施计划](../plans/2026-09-15-phase4-skill-evaluation.md)。
- 总入口：[Phase 4 总实施计划](../plans/2026-09-15-phase4-implementation-roadmap.md)。

本文记录实现边界和接口设计，不替代正式需求，也不包含会话推理过程。

## 1. 目标与依赖

前置：P4-A1 已验收。覆盖正式规格第 6、8、9、11.2–11.5、12.2、13–15、18 节。

交付八个首批技能、固定验收计划、自适应调查边界、EvidenceRef、EvaluationReport、离线 eval CLI 和扩充后的 24 个任务。完整 Diagnosis 不属于本批。

## 2. 架构

```text
TaskSpec + AgentRun + VerifierResult + 产物索引
  → EvidenceIndex（只读、按摘要定位）
  → EvalPlan（固定要求与基础路由）
  → SkillRegistry + 有限权限的执行上下文
  → EvaluationItem
  → EvidenceAudit
  → EvaluationReport + Core Evaluation 导出
```

- `evaluation/models.py` 兼容扩展 P4-A1 单项模型；不重新定义四态。
- `evaluation/evidence.py`：EvidenceRef、索引、解析和引用审计。
- `evaluation/skills/`：八个技能，各有输入输出和适用条件。
- `evaluation/planner.py`：requirements 到技能的固定映射及调查计划。
- `evaluation/engine.py`：执行、错误归一化和必需项完整性检查。
- `evaluation/report.py`：JSON、中文 Markdown 和 Core 导出。

## 3. 技能执行合同

Skill 声明 name、version、input/output schema、required_capabilities、permission_scope、timeout 和预算。运行返回 EvaluationItem 列表与证据引用，不直接修改 AgentRun。

八个技能沿用正式规格命名。verify_task_outcome 和 check_regression 在离线模式读取已有 verifier 结果；没有结果时返回 unknown，不自行运行测试。执行额外调查必须走已授权 gateway；首版默认不开启离线执行。

check_mcp_contract 校验实际 schema 与输入/结果；业务是否完成由 verify_external_state 负责。audit_verification_claims 可以使用受约束模型提取宣称，但测试日志等确定性证据优先。没有模型配置时对无法识别的宣称返回 unknown，不能伪造解析结果。

## 4. 路由、聚合与冲突

固定验收计划在候选产物可见前生成，输入仅为任务、要求和声明的场景能力。输出计划摘要与路由理由。执行时可以发现证据不可用，但不能免除必需项。

自适应调查仅扩展取证，不能改 rubric、提高某个候选的预算或跳过不利检查。任一技能故障只影响相应项；缺项自动补为 unknown，并保留 evaluator error。

复用 outcomes.py 聚合四态。有效 verifier 结果不能被 LLM 覆盖；存在矛盾时保留双方并标记需要审核的冲突。

## 5. 证据结构与 Core 映射

EvidenceIndex 以输入 bundle 及其授权根目录为边界，验证路径、摘要、JSON Pointer/行区间、run/span/artifact 归属。相同证据可被多个结论引用。

引用审计检查结构和来源，语义充分性通过规则和人工校准补充；存在引用不等于结论一定正确。

报告中的 Evaluation 使用 Core 模型。只有被测 run 内的证据进入 evidence_span_ids；verifier 或文件证据使用 report-level refs。导出副本保留源摘要和 assessment_id；再次评测不覆盖或无提示累计旧结果。

## 6. MCP 与采集衔接

完成 EVD-05：真实 Agent 调用的 server 身份、工具、参数、结果与 schema 对应；schema 无法获取时明确不可评。不得将单次 explicit selector capture 计为自主多步工具评测。

多步调用需要在受控任务中捕获完整工具链，source coverage 明确。McpTraceMapper 保持独立路径，不要求本批建设通用代理。

## 7. 数据、验收与风险

任务基准扩充至 24 个，12 Coding、6 MCP、6 组合；至少 12 个有真实来源，至少 8 个留出，按任务来源分组。manifest 校验来源、版本、划分和派生关系，防止只补数量不补可执行验收。

必须覆盖：无 finding 不等于通过、必需项漏判、跨 run 证据、历史无效 checks、引用摘要不匹配、LLM 无效输出、注入内容、已有文件保护和 eval 退出码。

产物和日志过大时应分块索引并声明截断，不把未读取部分当成不存在。质量门禁以引用有效、无确定性假通过、未知项正确处理为主；诊断优劣在 P4-B1 校准。

## 阶段技术报告

本批完成实现与实际验证后，创建 `docs/reports/phase4-skill-evaluation-technical-report.zh-CN.md`，按正式规格第 20.3 节记录技术选择、语法规则、设计模式、实现、真实验证与风险。当前不创建报告或占位文件。
