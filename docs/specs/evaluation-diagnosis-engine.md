# Phase 4：评测与诊断系统规格

- 版本：0.3
- 日期：2026-09-15
- 状态：P4-P 已人工评审、实现并完成本地验收；P4-A1/A2/B1/B2 仍为待评审/未实现范围。
- 适用范围：Phase 4 前置修复、4a Evaluation、4b Diagnosis。
- 文档用途：作为架构设计、实施计划、测试和分批验收的依据。

本文中的“必须”为验收要求，“可以”为可选能力。除下文明确标为已实现的 P4-P 外，其余新增命令、模块和数据结构仍为待实现设计。数值规模是本阶段的交付要求，不是对生产效果的保证。

## 1. 阶段目标

LumiAgent 应能接收真实 Coding Agent / MCP 任务及其执行证据，验证任务是否完成，说明执行中存在的问题，给出可审阅的诊断，并通过对照复跑检查改进效果。

本阶段必须回答五个问题：

1. 任务要求是否满足，哪些要求未满足？
2. 结论依据哪些测试、文件、工具结果或执行记录？
3. 失败出现在哪个操作或环节，可能由什么因素造成？
4. 下一步应修改什么，如何验证修改是否有效？
5. 哪些问题因为证据不足或能力限制而无法判断？

整体流程：

```text
任务说明与初始状态
  → 真实 Agent 执行与证据采集
  → 独立结果验证
  → 按任务选择过程检查并审核证据
  → Evaluation：是否满足要求
  → Diagnosis：原因、建议与验证方案
  → 人工确认改进
  → 相同条件下复跑与比较
```

## 2. 术语与职责

| 术语 | 含义 |
|---|---|
| Task（任务） | 一份明确要求、初始状态、约束和验收方式的可执行案例 |
| Trial（单次运行） | 某个 Agent 配置对某个任务的一次执行；同一任务可重复运行 |
| AgentRun | Phase 1 的执行记录模型；一次 Trial 可关联多条 AgentRun |
| Verifier（验证器） | 在受控环境中检查最终代码、文件或外部状态的程序 |
| Evaluation（评测） | 判断某项要求是否满足，并提供理由和证据 |
| Diagnosis（诊断） | 调查失败位置和原因，提出可验证的改进建议 |
| Skill（评测技能） | 具有适用条件、输入、输出和权限限制的可复用检查单元 |
| EvidenceRef（证据引用） | 指向特定运行、span、artifact 或文件版本中具体位置的引用 |
| Experiment（实验） | 将相同任务上的多次运行组织起来，用于比较配置或改进措施 |
| 留出集 | 不用于修改规则、提示词或诊断策略，只用于最终检验的数据 |

Evaluation 与 Diagnosis 按职责区分，不按是否使用 LLM 区分。两者均可使用程序、工具和受约束的 LLM 分析。

执行状态、任务结果和评测状态必须分别保存。一次工具报错不直接等于任务失败，所有工具返回成功也不直接等于任务完成。

## 3. 范围与非目标

### 3.1 本阶段必须交付

- 修复影响评测的证据引用、工具配对和时序问题。
- 支持离线 trace 审计和受控任务评测两种模式。
- 定义任务、单次运行、评测报告、诊断报告和最小实验记录。
- 支持真实 Claude Code 运行，以及受控 MCP 多步任务。
- 支持结果正确性、过程可靠性、约束安全和效率稳定性检查。
- 交付任务基准集、诊断校准集和改进验证记录。
- 提供 JSON 输出与便于人工阅读的中文报告。
- 对评测与诊断自身的工具调用、证据访问和结果生成进行 trace 记录。
- 隔离旧聊天评测实现，明确新的产品入口。

### 3.2 本阶段不做

- 自研通用 Coding Agent，或把自研 Agent 作为首个闭环的前置条件。
- 全量运行 SWE-bench 等大型外部基准，或建设公开排行榜。
- Web UI、完整 TUI、通用多 Agent 编排和生产级分布式调度。
- 通用 MCP Proxy、完整 SDK，或实现所有 MCP transport。
- 自动修改生产 Agent、生产数据或权限策略。
- 读取或要求模型的隐藏思维链。
- 强制复用 ReActEngine、RAGPipeline、MemoryManager 或旧 EvaluationSuite。
- 实现完整知识库或自动学习系统；仅保留可选知识查询接口。

现有 hooks → converter → AgentRun 路径继续保留。`ClaudeCodeHooksStrategy` 门面不作为 Phase 4 前置条件。

## 4. 首批使用场景

| 场景 | 任务验收重点 | 过程检查重点 |
|---|---|---|
| 仓库缺陷修复 | 目标缺陷修复，原有行为不回归 | 定位、修改、验证是否形成有效关联 |
| 跨文件接口变更 | 实现、调用方、配置和测试保持一致 | 是否遗漏依赖或只修复局部现象 |
| MCP 分页检索 | 多页数据处理完整，汇总结果可核验 | 参数生成、分页消费和终止条件 |
| MCP 状态更新 | 指定对象正确更新，其他对象不受影响 | 对象选择、权限、重试和重复写入 |
| Coding + MCP 工具链 | 获取任务上下文、修改代码并正确验证 | 外部信息、代码变更和结果判断的联系 |
| 只读或权限受限调查 | 分析有证据，不产生禁止的副作用 | 是否越权、擅自修改或虚报完成 |

普通任务不要求唯一工具顺序或唯一补丁。只有任务明确要求使用某接口时，才能将接口使用情况作为验收条件。澄清问题、安全停止或正确拒绝操作，可以是任务合同规定的正确结果。

## 5. 两种工作模式

### 5.1 离线 trace 审计

输入为已有 AgentRun，以及可选的任务说明、产物和环境记录。

- 默认只读取输入，不执行 trace 中的命令，也不连接外部服务。
- 仅对已有证据支持的事项作出判断。
- 缺少任务合同或独立验证结果时，不得宣布任务整体通过。
- 结果必须标明审计范围、采集缺口和未验证事项。
- 需要额外执行或访问外部系统时，生成待授权的调查请求，不自动执行。

### 5.2 受控任务评测

输入包括任务合同、可重置初始状态、Agent 配置和资源预算。

- 执行前检查环境、授权、依赖和数据隔离。
- 每次运行使用独立工作区；验证器使用受保护的验收材料。
- 执行结束后收集候选产物，并独立验证结果和副作用。
- 即使 Agent 崩溃、超时或拒绝执行，也必须保存 Trial 及已有证据。
- 环境启动失败应有单独记录，不得伪造 AgentRun 或静默跳过任务。
- 取消和超时后必须停止本次可控进程，释放资源，并记录清理结果。

## 6. 前置要求：证据可靠性

### EVD-01：引用完整

- 每个 finding、Evaluation 和 Diagnosis 的证据引用必须能解析到实际保存的对象。
- converter 不得把前一次构建的 span ID 留在重新构建后的 run 中。
- Core 结构校验之外，必须校验已知 adapter artifacts 内的引用。
- 历史无效 artifacts 保留原文并标记无效，不得直接用于正式结论。

### EVD-02：工具调用关联

- 优先使用源系统的调用 ID，并结合 session、子任务等范围信息配对请求和结果。
- 同名交错调用、乱序返回、重试、重复事件和缺失事件必须有测试。
- 缺少唯一关联信息时，必须标记歧义；不得仅按工具名强行配对。
- 重复采集同一源事件不得产生无提示的重复动作。

### EVD-03：时间与执行顺序

- 保存源时间、源序号和关联信息；语义分组不能覆盖原始顺序。
- 禁止用 Span Tree 深度优先遍历顺序推断真实执行先后。
- 并发操作只保留有依据的先后关系；无法确定的顺序必须显式说明。
- 转换时间必须与源执行时间区分。没有可靠源时间时，不得计算或展示为真实执行耗时。
- 任务的最终回答、错误和恢复动作必须按源信息关联，不得统一插到操作之前。

### EVD-04：采集能力与质量声明

每次转换或采集必须记录以下字段的已知状态及缺口：

- 调用 ID、源事件顺序、源时间与子任务关联。
- 参数、返回结果、错误和截断信息。
- MCP server 身份、工具名、schema 版本或摘要。
- 任务说明、最终回答、代码差异及最终状态。
- 模型、Agent 配置、资源、时间和费用信息。
- 未配对事件、采集中断、脱敏造成的信息损失。

缺少费用或时间数据时使用空值，不使用零值。不能仅凭 run 正常结束就声明采集完整。

### EVD-05：Coding 与 MCP 语义衔接

- 保留 MCP 工具的原始名称、server 身份、参数和返回值，避免无提示地归类为普通 shell 操作。
- schema 必须与实际使用的 server/工具版本对应；事后获取的不同版本不能冒充调用时证据。
- 已有单次显式 MCP capture 保留为连接和契约测试路径，不计为 Agent 自主选工具能力。
- 至少一条真实 Agent 多步 MCP 路径必须被归一化并用于阶段验收。
- Phase 3 workflow checks 只作为预检输入；使用前校验来源、版本、引用和适用范围。失效检查可以在当前输入上重新计算，但必须与历史结果区分。

### 6.1 P4-P 已实现的接口与兼容合同

2026-09-15 已完成本批实现与本地验收，详见 [P4-P 技术报告](../reports/phase4-evidence-readiness-technical-report.zh-CN.md)。完整任务评测仍由后续阶段实现。

| 接口/模型 | 本批行为 |
|---|---|
| build_hook_event / ClaudeCodeHookEvent | 新捕获写 v2；新增 capture_id、source_event_id、source_sequence、call_id、scope_id、observed_at；继续读取 v1 |
| correlate_events | 返回 actions、issues、duplicate_count；状态为 paired、unpaired、ambiguous、not_applicable |
| SourcePosition / source_relation | session/scope 范围内源序号及源起止时间；支持 before、after、concurrent、unknown，不使用树序或导入时间 |
| source_duration_ms | 仅有效源时间区间可返回毫秒数；单点观察、缺失或非法时间返回 None |
| CaptureCapabilities | 完整性由 workflow_coverage 与 coverage_basis 声明，其他可用性据实际采集计算；费用、最终状态等未采集项保持 unknown |
| audit_coding_evidence | 校验 Core、artifact ID、引用、版本、对象摘要和当前规则结果；返回整体及逐 artifact 状态 |
| refresh_workflow_checks | 在副本上追加当前规则结果，保留历史 artifact 和 supersedes_artifact_ids，不改原始输入 |

补充约束：

- legacy event_id / sequence 可能来自旧采集器默认值，不自动提升为可信源身份或序号；导入定位 ID 不用于证明源事件重复。
- converter 仅接收可选 coverage 的覆盖范围、依据和缺口，不继承调用者未提供证据的 costs/final_state 等可用性。
- 新 workflow checks 使用 `coding_workflow_checks.v2` 与 `coding_workflow.v2`，含 subject_digest 和 limitations；这是流程预检，不是正式 Evaluation。
- 缺完整性时，未观察到动作应为 unknown。证明覆盖完整的合成或受控输入可以发现确定缺失；该声明不代表密码学来源认证。
- 历史 unknown/invalid 仍保留在整体审计中；消费者须查看相应 artifact 的独立状态，不得把 supersedes 当成绕过校验的依据。
- MCP 原始身份和返回值已保留；schema 仅标为 unavailable/unverified，不声称已完成契约或业务语义评测。
- `lumi eval` 已改为仅给迁移提示并退出 2，旧入口为 `lumi legacy-eval`。正式 eval 功能仍未实现。
- `trace` 拒绝 session 路径越界、非法事件输入和覆盖已有输出；`show --checks` 区分当前证据与不可信历史状态。

## 7. 任务与单次运行合同

### 7.1 TaskSpec

| 字段组 | 必需内容 |
|---|---|
| 身份 | task_id、版本、任务族、来源、使用权限或许可 |
| 用户要求 | 任务说明、可接受结果、允许澄清或拒绝的条件 |
| 初始状态 | 仓库提交或状态快照、依赖锁定信息、MCP 数据种子 |
| 环境 | OS/运行时、镜像或环境摘要、网络策略、server 及 schema 摘要 |
| 约束 | 允许与禁止操作、文件范围、权限、时间和资源预算 |
| 验收 | 带稳定 ID 的要求、必需/可选标志、验证器和适用条件 |
| 恢复 | 初始化、重置、清理方法及其健康检查 |
| 数据划分 | 开发集或留出集、分组 ID、派生关系和脱敏状态 |

参考解、隐藏测试和预期故障标签属于受保护的验收资产，不包含在发送给 Agent 的 TaskSpec 视图中。

### 7.2 TrialRecord

每个 Trial 必须记录：

- trial_id、task_id、任务版本、实验 ID 和重复运行序号。
- Agent/模型版本、规则与 prompt 摘要、工具配置及其内容摘要。
- 初始状态、最终产物摘要、环境与资源配置。
- 被测 Agent、验证器、评测器和诊断器的 run 关联。
- 启动、结束、超时、取消和清理状态。
- 执行费用、验证费用、评测诊断费用，分别记录；未知值保留为空。
- 验证是否有效、无效原因和证据，以及各要求的评测结果。

同一配置不保证随机模型输出完全相同。可复现要求是输入、版本、环境、产物与执行记录可追溯，且可以按相同配置重新执行。

## 8. Evaluation 要求

### 8.1 四类评测

| 类别 | 必须覆盖的检查 |
|---|---|
| 结果正确性 | 目标缺陷或功能、回归行为、最终文件及外部状态 |
| 过程可靠性 | 调用契约、结果消费、修改与验证关系、错误恢复、完成宣称 |
| 约束与安全 | 禁止修改、越权、测试篡改、重复写入及其他禁止副作用 |
| 效率与稳定性 | 时长、费用、重复尝试、无效调用、重复运行结果与人工介入 |

结果检查优先使用独立验证器。代码通过测试不代表所有未测试行为都正确；报告必须限定结论适用范围。无法通过确定性程序判断的要求，可以使用带明确 rubric 的 LLM 辅助评测或人工审核。

### 8.2 单项状态与分数

| 状态 | 含义 | 分数规则 |
|---|---|---|
| pass | 有充分证据表明该要求满足 | 二元要求可为 1 |
| fail | 有充分证据表明该要求不满足 | 二元要求可为 0 |
| unknown | 证据不足、验证失败或无法可靠判断 | 必须为空 |
| not_applicable | 按预先定义的条件不适用 | 必须为空 |

连续分数只有在量纲、范围和评分规则预先定义时才能使用。没有 finding 不等于 pass；没有读取文件记录不等于上下文不足；出现测试命令不等于测试通过或验证充分。

任务总体结论按以下顺序确定：

1. 任一必需要求有有效 fail，任务为 fail，即使其他要求尚未知。
2. 没有必需 fail，但存在必需 unknown，任务为 unknown。
3. 所有适用的必需要求都有有效 pass，且不存在必需 unknown，任务才为 pass。
4. 没有适用的必需要求时，任务为 unknown，记录任务合同缺少有效验收项。

必需要求的“不适用”必须由固定任务条件支持，不得依据 Agent 输出临时免除。硬约束失败不能用其他高分抵消。首版不提供无明确含义的 Overall Score。

### 8.3 评测计划与技能

每份 EvalPlan 必须保存任务版本、要求 ID、所选技能、启用/跳过原因、预算和计划版本。

- 同一比较实验的验收要求、rubric 和基础技能路由必须一致，并在候选结果可见前固定。
- 可根据执行结果选择调查分支，但不得改变原有要求、分数标准或预算规则。
- 路由遗漏必需要求时，该要求为 unknown，不得视为通过。
- LLM 不可覆盖有效的确定性验证结果；冲突必须作为可审核问题保留。

首批技能：

| 技能 | 输出范围 |
|---|---|
| verify_task_outcome | 任务要求与独立 verifier 结果的对应关系 |
| check_regression | 受保护行为是否保持 |
| inspect_change_scope | 变更范围、禁止项与异常产物 |
| audit_verification_claims | 最终回答中的验证宣称是否有证据 |
| check_mcp_contract | 工具 schema、参数、返回结构与错误 |
| verify_external_state | 外部对象最终状态和禁止副作用 |
| analyze_recovery | 失败、相关恢复动作与成功复验的关系 |
| assess_evidence_quality | 引用、顺序、缺失和截断问题 |

每个技能必须声明版本、输入输出 schema、适用条件、权限、超时和失败处理。可选 KnowledgeProvider 首版允许为空，不要求安装向量数据库。

### 8.4 MCP 专项判断

- 区分连接/协议错误、工具执行错误和业务结果不满足。
- 区分 schema 合法与任务语义正确；合法参数仍可能指定错误对象。
- 工具返回成功后，写操作仍需检查实际对象状态与副作用。
- 工具不可用、权限不足、限流与 Agent 误用必须分别报告。
- 分页、部分返回、截断、重试及幂等性按任务合同检查。
- 没有任务目标、可选工具和必要上下文时，不得断言“选错工具”。

## 9. 独立验证与证据报告

### 9.1 VerifierResult

验证器必须输出：检查 ID、版本、被验证产物摘要、执行状态、检查结果、日志引用和资源记录。

验证器执行状态与检查结果分离。测试断言失败属于有效 fail；验证器无法启动或自身异常时，对受影响要求输出 unknown，并记录失败原因。不得把所有非零退出码一律当作 Agent 失败。

代码任务必须在干净基线中应用候选变更，再运行受保护的测试。数据库或文件任务必须使用受控初始状态和独立最终状态检查。真实服务任务需保存查询时间、租户范围和状态版本；状态漂移必须披露。

### 9.2 EvidenceRef 与证据结构

证据引用必须包含唯一引用 ID、来源类型和内容摘要；按来源补充 run_id、span_id、artifact_id、文件版本、JSON 路径或日志行区间。文件证据不得只保存可被后续运行覆盖的临时路径。

报告按“要求 → 结论 → 支持/反驳证据”组织。多项结论可共享证据，不要求复制执行 Span Tree。每条结论必须能查看：

- 检查了什么，为什么适用。
- 使用了哪个技能、验证器或人工标注。
- 证据来自哪里，是否完整。
- 哪些证据支持或反驳结论。
- 哪些问题仍未验证。

证据审计必须检查引用可解析性、来源与内容版本、关联关系和时间有效性。证据无效时不能通过审核。已知“未执行”的判断必须有观测范围或完整性依据，不能只引用一个不存在的操作。

### 9.3 与 Trace Core 的兼容

- 不向通用 Core 加入 Claude Code、MCP、Task 或环境专用必填字段。
- 新评测使用 Core Evaluation，状态放入 label；规则版本、要求 ID 和方法标识放入受约束的 metadata。
- 新诊断使用 Core Diagnosis；补充的假设、反证和干预方案由诊断报告结构承载。
- Core 的 evidence_span_ids 只能引用该记录所属 AgentRun 内的 span；跨 run 或文件证据使用报告级 EvidenceRef。
- 报告必须能单独保存，也可导出带结果的 AgentRun 副本；原始输入文件不得被覆盖。
- Task、Trial、Experiment 和跨 run 关系先放在评测层，不扩展 Core 以容纳尚未稳定的概念。
- 不把“被评测的 run”当成“触发评测器的父 run”。首版关联使用报告字段，避免误用 parent_run_id / triggered_by_span_id。
- 重复评测使用独立 assessment_id，保留版本和输入摘要；不得无提示地覆盖或重复追加为同一结果。

## 10. Diagnosis 要求

### 10.1 输入与输出

输入包括任务合同、Evaluation、原始证据和可选补充调查结果。Diagnosis 不能只读取失败标签后套用固定建议。

每条诊断必须包含：

| 项目 | 要求 |
|---|---|
| 关联问题 | 对应要求和 Evaluation ID |
| 观察事实 | 可直接由证据支持的失败现象 |
| 位置 | 动作、span、文件或时间区间；不确定时明确说明 |
| 原因状态 | hypothesis（待验证假设）或 intervention_supported（有干预证据支持） |
| 责任层 | Agent 决策、上下文、工具/schema、环境、权限、采集或评测器 |
| 证据 | 支持证据、反证、备选解释及缺口 |
| 建议 | 修改对象、具体措施、风险和人工确认要求 |
| 验证方案 | 改动因素、固定条件、预期变化、失败判据和回归检查 |

允许一个任务有多个贡献因素，不强制唯一根因。没有足够证据时返回 abstained（暂不归因）及缺口，不生成虚构的 Core Diagnosis。失败类型和责任层分别保存，不能把工具报错直接归因为模型能力不足。

### 10.2 首批归因范围

- 上下文缺口：任务相关信息未获得或未使用，且有证据支持。
- 工具误用：错误对象、工具选择、参数或调用条件。
- 结果误读：与工具输出、状态或测试记录相矛盾的后续行为或宣称。
- 验证不足：必需检查缺失、验证对象或版本不匹配。
- 恢复问题：未处理相关错误、重复失败或不安全重试。
- 约束违反：禁止修改、越权或其他明确禁止的副作用。
- 非 Agent 问题：环境、采集、验证器或任务合同本身的问题。

不要求为每次失败都输出上述类别。故障标签不作为归因模型可见的输入。

### 10.3 自身可观测

评测和诊断必须记录所用版本、可审阅的检查计划、工具调用、证据访问、结果、超时和费用。不要求保存模型隐藏思维链。评测器的动作不得混入被测 Agent 的执行记录，也不得计入其完成时间或费用。

## 11. 基准数据与构造规范

### 11.1 三类独立资产

| 数据集 | 评测对象 | 内容 |
|---|---|---|
| 任务基准集 | 被测 Coding Agent / MCP 系统 | 可执行任务、环境和受保护的验收材料 |
| 诊断校准集 | LumiAgent 的评测与诊断能力 | 脱敏轨迹、结果、人工标签和证据 |
| 改进验证记录 | 建议的实际作用 | 基线、干预、复跑、回归检查和比较报告 |

### 11.2 任务规模与来源

Phase 4 完整验收要求至少 24 个种子任务：12 个 Coding、6 个 MCP、6 个组合任务，覆盖第 4 节六类场景。首个可执行批次可以先交付其中 6 个：每类任务族 2 个。

- 至少 12 个任务来源于可追溯的真实 issue、修复提交或经授权的实际需求，且三个任务族均有真实来源。
- Coding 覆盖至少两个独立仓库；MCP 覆盖至少两类真实 server，其中一类涉及可独立验证的状态更新。
- 使用真实 Agent 执行自然语言任务，不能用固定操作脚本冒充 Agent 工具选择能力。
- 合成任务用于补充边界覆盖，必须标记构造方式。
- 原有小型样例和 Phase 1–3 fixtures 可继续作为回归测试，不自动计入真实任务数量。
- A1/A2 公开评测集来源池与抽取规则见 [`benchmarks/eval-suite/SOURCE_CATALOG.md`](../../benchmarks/eval-suite/SOURCE_CATALOG.md)。该目录只锁定借鉴对象，不替代本小节的规模、真实来源和审核要求。

### 11.3 任务构造与审核

每个任务必须依次完成以下检查：

1. 记录来源、使用权限、任务要求和脱敏范围。
2. 固定初始状态、依赖、工具及环境配置。
3. 定义目标结果、回归要求、硬约束和 verifier。
4. 验证未修改方案失败、参考完成方式通过；无需修改的任务则验证正确只读结果和错误副作用。
5. 用至少一个常见错误产物或错误状态验证检查有效，不能只验证参考解通过。
6. 在重置环境后重复执行 verifier，确认结果稳定；不稳定项必须标记并修复或退出正式比较集。
7. 审核任务说明与验收条件一致，允许合理的替代实现。
8. 完成开发集/留出集划分后发布版本。

### 11.4 数据划分与防泄漏

- 24 个种子任务至少保留 8 个作为留出集，覆盖三个任务族。
- 同一 issue、模板派生任务和高度相关的仓库变体必须同组划分；禁止按 trace 随机拆分造成泄漏。
- 留出集不得用于修改规则、prompt、技能路由或诊断策略。使用后若据此调参，必须记录并建立新的留出版本。
- 参考解、隐藏测试和故障标签与 Agent 工作区及诊断输入隔离。
- 不提交生产凭证、私有原始会话或未获授权的代码。

### 11.5 压力变体

任务可增加分页、结果截断、工具歧义、暂时故障、权限限制、交错调用、重复事件和恶意内容等条件。必须保存注入位置、随机种子或可重放事件，以及与种子任务的关系。

压力变体单独报告，不算新的独立种子任务。注入标签对被测 Agent 和诊断器隐藏。自然失败与受控失败分开统计。

### 11.6 诊断校准集

Phase 4b-1 至少交付 48 条经人工审核的轨迹，覆盖成功、失败、恢复成功、硬约束违反、环境/评测器问题和证据不足六类，每类至少 4 条。

- 至少一半来自未注入故障的真实 Agent 执行，不能全部使用手写轨迹。
- 至少 16 条作为留出轨迹，按任务来源分组；不得与用于调参的同任务轨迹混用。
- 标签包含结果、可接受失败类别、关键证据、可接受替代解释和是否应弃判。
- 每条标签由一名审核者标注、另一名审核者复核；争议保留记录，无法确定的原因不强行成为标准答案。
- 预期失败模式只用于任务设计，不能代替实际运行标签。

这些规模用于初步验收和发现问题，不足以证明广泛生产泛化能力。

## 12. 改进实验与指标

### 12.1 对照复跑

- 每个实验先固定任务集、验收条件、重复次数、主要指标和无效运行判据。
- 至少比较基线与一个干预配置；一次只改变一个主要因素。
- 固定模型/Agent 版本、初始状态、工具、预算和环境中不属于干预的因素。
- 每个配置对每个入选任务至少运行 3 次；报告波动，不将少量成功解释为稳定保证。
- 动态外部状态应冻结、记录重放或进行成对时间控制；无法控制时明确限制比较结论。
- 不选择性删除失败运行。配置预算超限、故障注入和错误恢复本身属于测试目标时，不得记为无效基础设施运行。
- 修改提示词、工具或工作流前必须由用户确认；无批准时仅保存建议与实验计划。

### 12.2 被测系统指标

必须报告任务完成率、硬约束违反率、回归率、人工介入、重复运行稳定性、耗时及费用。每项指标保存分子、分母、未知值数量和排除原因。

- 端到端完成率的分母包括全部已调度 Trial；启动失败、取消、unknown 等单独列明。
- 可另报有效运行上的完成率，但必须同时给出无效运行数量和依据。
- unknown 不算成功，不从主指标分母中自动移除。
- 单位成功任务成本包含有效比较范围内失败尝试的费用；无成功或费用不完整时不得输出误导性数字。
- 重复运行报告每个任务的通过次数及所有重复均通过的任务比例，不假设各次运行独立。

### 12.3 LumiAgent 自身指标与基线

在同一留出集上比较：确定性规则、固定输入范围的单次 LLM Judge、技能化评测诊断方案。使用同一证据访问政策和验收定义；记录模型、预算及费用差异，不能把额外访问隐藏标签的结果作为优势。

必须报告：

- 结果判断的混淆表，尤其是假通过和假失败。
- 证据引用有效率、证据充分性审核结果。
- 失败类别、责任层、关键位置及备选解释的审核结果。
- unknown / abstained 比例，以及错误地确定归因的比例。
- 建议可操作性、干预结果和新增回归。
- 评测诊断成本与执行时间。

自动校验的硬门槛：受验报告的引用全部有效；确定性控制样例无假通过；缺失证据不被当作正向证据。诊断质量的人工评分表、主指标和最低阈值必须在留出集运行前随版本冻结，不能看完结果后补定。

若复杂方案未达到冻结阈值，或未表现出相对简单基线的可解释收益，4b 不得宣称验收通过。不得通过更换失败样本规避此要求。

## 13. 架构与存储边界

目标模块布局：

```text
src/lumiagent/
  tracing/             通用 Core，保持既有兼容性
  adapters/coding/     Coding 语义、归一化与证据规则
  adapters/claude_code/源事件采集、转换与能力声明
  adapters/mcp/        MCP 证据、schema 与 runtime
  evaluation/          任务合同、技能、计划、证据审计与 Evaluation
  diagnosis/           假设、证据调查、建议与 Diagnosis
  benchmarks/          runner、环境、verifier、Trial 与 Experiment
  legacy_eval/         隔离后的旧聊天评测
```

CLI 只负责参数、编排和展示，不承载场景判定逻辑。Core 不反向导入 adapter、benchmark 或诊断模块。

存储要求：

- 提交到仓库：任务清单、允许公开的环境定义、测试、脱敏样例及报告模板。
- 本地运行目录：原始采集、产物快照、verifier 日志、评测报告和实验记录；默认位于被忽略的 `.lumiagent/` 下。
- 任务资产按公开输入与受保护验收材料分区；不能依靠“文件名隐蔽”保护隐藏测试。
- 报告以 JSON 为机器可读主格式，中文 Markdown 为人工阅读格式；二者由同一结构化结果生成。
- 模型输出解析失败时记录 evaluator error，对受影响项返回 unknown，不输出伪造的有效结果。

## 14. CLI 与旧评测迁移

### 14.1 新命令合同

以下命令为计划接口，当前仓库尚未实现：

```text
lumi eval <trace.json> --output <report.json>
lumi eval <trace.json> --task <task.json> --output <report.json>
lumi diagnose <report.json> --output <diagnosis.json>
lumi bench run <suite> --agent <config> --repeat 3 --output <experiment-dir>
lumi bench run <suite> --experiment <experiment.json> --output <experiment-dir>
lumi bench calibrate <calibration-manifest> --policy <acceptance.json> --output <calibration-dir>
lumi experiment show <experiment-dir>
lumi experiment compare <baseline-dir> <candidate-dir>
```

- `eval` 默认离线审计，不因传入任务文件自动执行命令。
- `diagnose` 默认只读；需执行调查时必须通过受控、授权的执行接口。
- `bench run` 必须通过环境与授权检查，并明确预计的运行次数和预算上限。
- `bench run --experiment` 从已注册实验读取候选配置与重复次数，与 `--agent` / `--repeat` 互斥；必须另行验证实验授权。
- `bench calibrate` 用于阶段诊断校准，必须验证审核清单、开发/留出隔离和冻结的验收政策；模型只读取证据视图，评分器才可读取标签。
- 输出路径已存在时默认拒绝覆盖。报告保留对源 trace 的引用，不移动或修改源文件。
- 全部命令支持 `python -m lumiagent.cli` 的等价入口。当前安装入口以 `lumi` 为准，不把未声明的 `lumiagent` 可执行名当作已存在能力。

默认退出码：0 表示命令完成并写出有效结果，不代表被测任务通过；2 表示参数、输入或不允许的覆盖；3 表示编排/评测器故障导致本次请求未完成；130 表示取消。已记录为 Trial 结果的 Agent 失败不会使批量命令停止。

`eval` 和 `bench run` 提供 `--fail-on-task-failure`：请求已完整处理时，存在 fail 返回 1；没有 fail 但有 unknown 或无效 Trial 返回 4；全部任务可确认通过返回 0。参数、编排故障和取消优先使用上述专用退出码。

### 14.2 Legacy 迁移

- 原 `lumiagent.evaluation` 迁至 `lumiagent.legacy_eval`，新评测使用正式 `evaluation` 包名。
- 原聊天评测命令改为 `lumi legacy-eval`，帮助中明确遗留、非 Phase 4 和不保证当前可用性。
- 新 `eval` 就绪前，旧 `eval` 调用仅给出迁移提示并退出，不自动启动聊天打分。
- 新入口只接受 trace/任务合同，不静默把旧 eval-set 名称解释成新输入。
- 更新内部 import、样例标识、CLI help 和包描述，并加入入口迁移测试。
- 不为迁移扩展旧评分能力，也不把旧 EvaluationSuite 接入新 pipeline。

## 15. 安全与权限

- 任务、仓库、trace、MCP 返回和 Agent 回答均是待评数据，不是评测器指令。
- 评测计划只能调用已注册技能和已授权工具，禁止直接执行不可信文本中的命令。
- Agent、verifier 和诊断工具使用独立权限；运行用户提供的代码必须在受限制环境中完成。
- 隐藏测试、参考解、标签、生产凭证与被测 Agent 隔离。
- MCP 写任务使用专用测试资源和最小权限；未授权的外部副作用禁止发生。
- 所有执行设置超时、资源和费用边界；重试必须有次数上限及副作用处理规则。
- 原始敏感数据只在授权范围内保存；外发给 LLM 前执行脱敏和数据访问检查。
- 脱敏会影响判断时，报告保留证据缺口，不补造内容。

## 16. 分批交付与验收

| 批次 | 必须交付 | 退出条件 |
|---|---|---|
| P4-P：前置修复与迁移（已完成本地验收） | EVD-01 至 EVD-05 中的基础关联、顺序、能力声明；legacy 隔离设计与实现 | 新增反例测试通过；无效历史证据被识别；既有 Phase 1–3 行为回归通过 |
| P4-A1：任务与结果验证 | TaskSpec、TrialRecord、首个真实 Agent runner、独立 verifier、6 个种子任务 | Coding/MCP/组合各 2 个任务可重置执行；通过、失败和环境异常均可记录 |
| P4-A2：技能化评测 | 全部 EVD 要求、技能注册、EvalPlan、证据审计、24 个任务、Evaluation/CLI | 必需项不被漏判；引用有效；unknown 和不适用正确；真实多步 MCP 路径可验收 |
| P4-B1：诊断与校准 | Diagnosis、48 条审核轨迹、基线比较、自身 trace | 预先冻结的质量阈值通过；能处理多原因、反证和弃判；建议带验证方案 |
| P4-B2：改进验证 | 最小 Experiment、成对复跑、结构化比较 | 完成至少两个不同改进层级的受控实验；至少一个有正向结果且无新硬约束违反，另一个如实报告有效/无效/负向结果 |

P4-B2 的实验必须覆盖 Coding 与 MCP/组合场景；每个实验至少包含 4 个未用于调参的任务和每配置每任务 3 次运行。正向结果仅在预先定义指标与检查范围内成立，不扩展为一般因果保证。

本阶段所有功能验收都必须有规格、实现计划、代码、自动化验证、可执行样例和中文技术报告。每批验收清单引用本规格的章节或要求 ID。前置修复未通过前，可以编写设计和测试，但不能发布正式可信评分。

## 17. 必需测试清单

| 测试组 | 必需案例 |
|---|---|
| 证据 | 重建后引用、历史悬空引用、artifact 内引用、跨 run 引用、输入不被覆盖 |
| 调用关联 | 同名并发、乱序返回、缺失请求/结果、重复事件、重试 |
| 时序 | 测试失败→修改→测试成功、交错验证、源时间缺失、最终回答位置 |
| 评测边界 | 空 trace、部分 trace、无适用要求、未知状态、缺费用、未观察到不等于未发生 |
| 验证器 | 未修改失败、参考方案通过、错误方案被拒、验收文件篡改、验证器崩溃 |
| MCP | 参数合法但对象错误、分页、部分成功、权限拒绝、响应丢失后的重复写入 |
| 诊断 | 明确原因、多原因、反证、环境问题、标签不可见、证据不足时弃判 |
| 安全 | 工具结果和报告中的指令注入、隐藏资产隔离、未经授权的复跑被阻止 |
| 比较 | 同条件重复、失败不被丢弃、unknown 分母、任务版本不匹配被拒绝 |
| CLI | 遗留提示、新旧输入分离、错误退出码、已有输出保护、取消后的记录与清理 |

实现阶段必须运行 pytest，以及覆盖 tracing、adapters、capture、新增 evaluation、diagnosis、benchmarks 和相关测试的 lint/type 检查。新模块不能因尚未出现在旧验证命令中而漏检。

真实路径验收必须额外执行任务与 verifier；单元测试和合成 fixture 不替代真实执行。环境无法满足时记录阻塞项，不标记该批完成。

## 18. 数据格式、映射与验证示例

### 18.1 版本与验证规则

- 新合同使用 Pydantic v2 模型，明确必填与可空字段，拒绝未声明字段；扩展信息只能放入已定义的扩展对象。
- Task、Trial、报告、证据引用和实验记录分别带 schema_version。任务内容版本与 schema 版本分开记录。
- ID 在同一存储范围内唯一；数组引用必须校验目标类型、对象存在性和所属版本。
- 内容摘要使用 SHA-256；比较实验在运行前固定任务、配置、环境、rubric 和 verifier 摘要。
- 旧版本读取要么显式转换并记录转换版本，要么报不支持；禁止按新格式静默猜测。
- 下面是合同的最小对象示例，不是已经执行的记录；摘要为格式示例，不能作为真实校验值。

### 18.2 单项结果与证据

```json
{
  "schema_version": "evaluation_item.v1",
  "requirement_id": "fix_pagination",
  "status": "fail",
  "score": 0.0,
  "reason": "两页输入的完整性检查失败，结果仅包含第一页。",
  "method": "deterministic_verifier",
  "method_version": "pagination_check.v1",
  "evidence_ref_ids": ["evidence_pages"],
  "limitations": []
}
```

```json
{
  "schema_version": "evidence_ref.v1",
  "evidence_ref_id": "evidence_pages",
  "source_type": "artifact",
  "run_id": "run_verifier",
  "span_id": "span_verify_pages",
  "artifact_id": "artifact_verify_result",
  "uri": null,
  "location": {"json_pointer": "/checks/fix_pagination"},
  "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

映射要求：`requirement_id` 对应 TaskSpec 中的要求；`status` 对应 Core Evaluation.label；本例的外部 verifier 证据保存在报告引用表中，不写入被测 AgentRun 的 evidence_span_ids。完整报告还必须包含 assessment_id、输入摘要、计划版本、各要求的结果与引用表。

`location` 是有类型的联合对象：JSON Pointer、文件行区间或整个对象三种形式互斥。artifact 类型必须指定 run_id、span_id、artifact_id；文件类型必须指定受控 URI 和内容摘要。两种类型不能混用不相干的定位字段。

### 18.3 诊断结果

```json
{
  "schema_version": "diagnosis_item.v1",
  "diagnosis_item_id": "diagnosis_pagination",
  "evaluation_requirement_ids": ["fix_pagination"],
  "failure_type": "result_misinterpreted",
  "responsibility_layer": "agent_decision",
  "cause_status": "hypothesis",
  "observation": "返回结果包含 next_cursor，后续未观察到续页请求。",
  "summary": "分页信息可能未被正确消费；当前仅作为原因假设。",
  "supporting_evidence_ref_ids": ["evidence_pages", "evidence_call_result"],
  "opposing_evidence_ref_ids": [],
  "alternative_explanations": ["后续调用可能未被完整采集。"],
  "suggested_fix": "核对工具分页说明，并增加分页完成条件。",
  "verification_plan": {
    "changed_factor": "工具分页说明",
    "fixed_factors": ["任务", "模型", "初始状态", "预算"],
    "expected_effect": "多页任务完整处理，单页行为无回归",
    "requires_approval": true
  }
}
```

本例须在完整报告中补齐两个证据对象并通过引用校验；没有证据的示例不得导出为有效报告。hypothesis 不等于已证明根因。intervention_supported 必须关联实际实验记录；无足够证据时生成报告级 abstained，不构造虚假的 Core Diagnosis。

### 18.4 执行流与存储映射

```text
TaskSpec + AgentConfig
  → Environment.prepare / healthcheck
  → AgentRunner.run → 被测 AgentRun + 候选产物
  → Verifier.verify → 独立 verifier run + VerifierResult
  → EvaluationEngine.assess → EvalPlan + EvaluationReport
  → DiagnosisEngine.diagnose → DiagnosisReport + 独立 diagnosis run
  → Experiment.compare → 指标、限制与改进结论
```

离线模式从已有 AgentRun 进入 EvaluationEngine，不调用 Environment、AgentRunner 或 Verifier 的执行接口。各接口均通过明确的输入、输出模型交换数据，不能在 CLI 中复制判断逻辑。

## 19. 风险与处理要求

| 风险 | 必须采取的措施 | 验证方式 |
|---|---|---|
| 采集缺失或并发顺序不明 | 能力声明、关联校验、局部弃判 | 缺事件、同名并发和部分顺序测试 |
| 工具/schema 漂移 | 保存实际版本与摘要，禁止冒用事后版本 | 版本冲突与重放测试 |
| 环境或 verifier 不稳定 | 环境健康检查，分离执行异常和有效失败 | 启动失败、flaky verifier 和预算超限测试 |
| LLM 过度归因或受注入影响 | 限制工具、校验结构、审核证据，支持弃判 | 恶意 trace、反证和空证据测试 |
| 留出集被反复调参 | 分组划分、冻结版本、记录使用与退役 | manifest 与实验审计 |
| 统计样本不足 | 报告原始计数、波动、未知项和适用范围 | 小样本和无成功样本报告测试 |
| 执行预算失控或产生副作用 | 授权、隔离、超时、有限重试和清理 | 拒绝执行、取消、重复写入测试 |
| 计划和实现漂移 | 每批重新核对正式规格与设计、记录偏差 | 实施计划覆盖表与最终技术报告 |

## 20. 文档分工与阶段技术报告

### 20.1 文档分工

| 位置 | 内容 | 状态要求 |
|---|---|---|
| docs/specs/ | 正式需求、接口合同、行为、非目标与验收标准 | 唯一事实来源；变更先更新规格 |
| docs/superpowers/specs/ | 有日期的阶段设计、架构边界、接口与数据流 | 链接正式规格；未评审不得写 approved |
| docs/superpowers/plans/ | Goal、Architecture、Tech Stack、File Structure、Task、Files、测试与预期结果 | 未执行步骤保持未勾选；依赖阶段未验收不进入实现 |
| docs/reports/ | 阶段实现技术报告 | 代码和验证完成后创建，不保存规格交付记录或文档修改日志 |
| docs/HANDOFF.zh-CN.md | 当前状态、文档入口、阻塞项与下一步 | 简要记录，不代替技术报告 |

正式规格由本文件统一维护；五个子阶段的设计和实施计划分别成文，不复制五份相互漂移的正式合同。主计划只组织依赖和入口，不替代各阶段任务。

### 20.2 阶段文档索引

| 批次 | 设计 | 实施计划 |
|---|---|---|
| P4-P | [证据就绪设计](../superpowers/specs/2026-09-15-phase4-evidence-readiness-design.md) | [前置实施计划](../superpowers/plans/2026-09-15-phase4-evidence-readiness.md) |
| P4-A1 | [任务验证设计](../superpowers/specs/2026-09-15-phase4-task-verification-design.md) | [任务验证计划](../superpowers/plans/2026-09-15-phase4-task-verification.md) |
| P4-A2 | [技能评测设计](../superpowers/specs/2026-09-15-phase4-skill-evaluation-design.md) | [技能评测计划](../superpowers/plans/2026-09-15-phase4-skill-evaluation.md) |
| P4-B1 | [诊断校准设计](../superpowers/specs/2026-09-15-phase4-diagnosis-calibration-design.md) | [诊断校准计划](../superpowers/plans/2026-09-15-phase4-diagnosis-calibration.md) |
| P4-B2 | [改进实验设计](../superpowers/specs/2026-09-15-phase4-improvement-experiments-design.md) | [改进实验计划](../superpowers/plans/2026-09-15-phase4-improvement-experiments.md) |

依赖、执行门禁与全阶段覆盖见 [Phase 4 总实施计划](../superpowers/plans/2026-09-15-phase4-implementation-roadmap.md)。P4-P 已实现并完成本地验收；其余四批设计与计划仍待评审、未执行。

### 20.3 技术报告要求

每批完成实现和验证后，分别创建下列报告。P4-P 报告已按真实结果创建；其余路径仅预留，不创建占位文件：

- `docs/reports/phase4-evidence-readiness-technical-report.zh-CN.md`
- `docs/reports/phase4-task-verification-technical-report.zh-CN.md`
- `docs/reports/phase4-skill-evaluation-technical-report.zh-CN.md`
- `docs/reports/phase4-diagnosis-calibration-technical-report.zh-CN.md`
- `docs/reports/phase4-improvement-experiments-technical-report.zh-CN.md`

每份报告必须包含：阶段目标与实际范围、技术选择、语法与风格规则、架构与设计模式、实际接口和实现亮点、测试命令与真实结果、真实路径验证、兼容性及偏差、风险与取舍、后续建议。

只能记录实际执行结果；预期通过、计划运行、外部环境不可用不能写成验收完成。未完成状态写入计划和 HANDOFF，不用提前生成报告来替代实现。提交代码或报告需要遵守独立的提交授权，不因计划存在而自动提交。

## 21. 文档衔接与后续阶段

本规格取代早期 Phase 4 中以下要求：

- 将全部 Evaluation 与 Diagnosis 绑定为一个必须复用旧 Agent 基础设施的实现。
- 首个闭环必须先实现 LumiAgent 自己的 Coding Agent。
- 使用旧 EvaluationSuite 作为新评测的起点。
- 仅以一次 test_command 退出码代表完整任务验收。
- 将最小 Trial/Experiment 与改进复跑全部推迟到 Phase 5。

Phase 5 继续负责 timeline、span detail、报告展示、trace diff 和实验比较 view model，复用 Phase 4 的数据，不重新定义评分或实验语义。

Phase 6 的通用 SDK/Proxy、Phase 7 Web UI 和 Phase 8 知识库保持后续范围。Phase 1–3 的历史交付记录保留；本规格的新增要求是面向正式评测的补充，不将已有阶段重新标为未完成。

相关文档：

- [项目总规格](../PROJECT_SPEC.zh-CN.md)
- [Coding Agent Trace 规格](coding-agent-trace-model.md)
- [MCP 采集与展示规格](mcp-capture-display-chain.md)
- [早期闭环设计（历史参考）](../superpowers/specs/2026-05-27-agent-evaluation-optimization-loop-design.md)
- [交接记录](../HANDOFF.zh-CN.md)
