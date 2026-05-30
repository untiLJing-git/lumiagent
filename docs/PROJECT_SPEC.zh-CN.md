# LumiAgent 项目规格说明

## 1. 核心定位

LumiAgent 是一个 Agent 评测与优化闭环，将 Agent 评测从一个分数，推进为一条可执行的改进路径。Benchmark 能回答 Agent 是否成功，LumiAgent 进一步回答：执行过程如何展开，失败在哪一步形成，诊断依据来自哪些证据，以及下一轮最值得优化什么。

产品闭环是：

```text
运行任务 → 采集轨迹 → 诊断失败 → 审阅证据 → 应用改进 → 对比复跑
```

在这个闭环下，LumiAgent 提供通用 Agent Trace / Eval Core，将 LLM、Tool、RAG、Memory、Evaluator、Fallback、Error 等执行节点统一建模为可嵌套的 Span Tree，使 Agent Run 可以被结构化记录、逐步回放、指标评测和失败归因。

首个落地场景聚焦 Coding Agent 与 MCP Tool Chain，通过采集文件检索、代码读取、代码修改、命令执行、测试验证、MCP 工具发现、工具调用、参数生成和工具结果等轨迹，诊断 Agent 在上下文收集、工具选择、参数正确性、结果使用、验证充分性、失败恢复和风险控制中的问题，从而优化 Coding Agent 的整体工作流。

## 2. 背景判断

当前业界已经存在 LangSmith、Langfuse、Phoenix、AgentOps、Braintrust、Helicone、LangGraph Studio 等产品，通用 LLM tracing、prompt management、dataset evaluation、RAG evaluation、agent session observability 等能力已经比较成熟。

因此 LumiAgent 不应定位为泛化 LLM observability 平台，也不应成为开源版 LangSmith 或 Langfuse。LumiAgent 的差异化应来自：

- Coding Agent 执行轨迹建模
- MCP Tool Chain 观测与诊断
- 面向 Coding Agent 工作流的评测体系
- 受 AI Profiling 启发的 Timeline / Span / Failure Diagnosis 体验

## 3. 当前主线

LumiAgent 当前主线由四部分组成：

1. 通用 Agent Trace / Eval Core
2. Coding Agent Trace
3. MCP Tool Chain Observability
4. Agent Evaluation / Diagnosis

其中通用 Core 负责定义 Run、Span、Event、Artifact、Evaluation、Diagnosis 等基础模型；Coding Agent 与 MCP Tool Chain 是首个落地场景和适配层。

## 4. 非目标

在当前阶段，LumiAgent 不做以下方向：

- 泛化 LLM observability dashboard
- Prompt 管理平台
- 通用 RAG evaluation 平台
- 大而全 Agent 框架
- 通用多 Agent 编排框架
- 仅用于替代 LangSmith、Langfuse、Phoenix 或 AgentOps 的平台

这些能力可以作为辅助能力存在，但不能成为当前阶段的主线。

## 5. 核心模块

### 5.1 Trace / Eval Core

负责定义通用 Agent 执行数据模型：

- Agent Run
- Span Tree
- Event
- Artifact
- Evaluation
- Diagnosis
- Experiment
- Annotation

核心要求：

- 框架无关
- 可嵌套
- 可序列化
- 可回放
- 可评测
- 可扩展到不同 Agent 框架和工具协议

### 5.2 Coding Agent Trace

面向 Coding Agent 的执行过程建模：

- user_prompt
- file_search
- file_read
- code_edit
- shell_command
- test_run
- browser_verify
- git_diff
- final_response

目标是解释 Coding Agent 如何理解需求、收集上下文、修改代码、执行验证和处理失败。

### 5.3 MCP Tool Chain Observability

面向 MCP 工具链的观测与诊断：

- MCP server connection
- tool discovery
- tool schema
- tool selection
- tool argument generation
- permission / approval
- tool execution
- tool result
- tool error
- tool latency

目标不是简单"支持 MCP"，而是看清 Agent 如何使用 MCP 工具链，以及工具链失败发生在哪一层。

### 5.4 Evaluation / Diagnosis

面向 Agent 工作流的评测与诊断能力：

- context gathering diagnosis
- tool selection diagnosis
- tool argument diagnosis
- tool result faithfulness
- verification sufficiency
- failure recovery diagnosis
- risk control diagnosis

输出应包含：

- score
- reason
- evidence span
- failure type
- suggested fix

## 6. MVP 阶段规划（近期）

### Phase 1: Trace Schema / Span Tree Core — 已完成

目标：建立 LumiAgent 的核心数据模型。

正式规格：`docs/specs/trace-core-mvp.md`。

交付物：

- Run / Span / Event / Artifact / Evaluation / Diagnosis 模型
- JSON 序列化能力
- 基础单元测试
- 示例 trace 数据

验收标准：

- 可以用统一 Span Tree 表达一次简单 Agent Run
- 可以序列化为稳定 JSON
- 测试覆盖核心模型创建、嵌套和序列化

### Phase 2a: MCP Tool Chain Model — 已完成

目标：建立 MCP 工具链观测模型，并作为后续 Coding Agent Trace 与 Evaluation / Diagnosis 的结构化证据层。

正式规格：`docs/specs/mcp-tool-chain-model.md`。

交付物：

- MCP server / tool discovery / tool call / tool result span
- tool schema 与 argument 记录结构
- MCP failure taxonomy 与 evidence fields
- error / latency / permission 字段
- 成功与失败示例 MCP tool chain trace

验收标准：

- 可以表达一次 MCP tool discovery 到 tool result 的完整链路
- 可以记录工具参数、结果、错误和耗时
- 可以识别工具调用失败类型

### Phase 2b: MCP 采集 + 展示链

目标：为 MCP trace 打通最小采集-模型-展示闭环，并建立所有未来采集策略共用的统一采集入口。

交付物：

- `CaptureStrategy` 协议，作为统一采集入口（策略模式）
- `McpCaptureStrategy` 作为首个实现：程序化调用真实 MCP Server，记录完整链路（connection、discovery、schema、call、result），使用 Phase 2a 的 builder helpers 生成 AgentRun
- `lumiagent capture mcp <args> -o trace.json` CLI 命令
- 最小 MCP trace CLI Viewer：`lumiagent show <trace.json>` 打印 MCP span tree、failure type 和 evidence fields
- 至少一个来自真实 MCP Server 交互的 trace

`CaptureStrategy` 协议是所有未来采集方式的共享入口：

```text
CaptureStrategy
├── McpCaptureStrategy          (Phase 2b)
├── ClaudeCodeHooksStrategy     (Phase 3)
├── TranscriptImportStrategy    (未来)
├── SdkDecoratorStrategy        (Phase 6)
└── McpProxyStrategy            (Phase 6)
```

各策略的具体采集机制在该策略实现时定义。

验收标准：

- 真实 MCP Server 交互可以被采集并转为合法 AgentRun
- trace 可以用 `lumiagent show` 查看，展示 MCP 特有信息（failure type、schema、arguments、result consumption）
- `CaptureStrategy` 协议已定义且可扩展

### Phase 3: Coding Agent Trace Model

目标：建立 Coding Agent 执行轨迹模型，并通过真实 Agent 数据验证。

交付物：

- file_search / file_read / code_edit / shell_command / test_run / git_diff span
- 一次 coding task 的完整示例 trace
- 基础 workflow validator

织入 — Claude Code hooks 采集：

- `lumiagent setup claude-code` 一键配置命令，在 `.claude/settings.json` 中注册 `PreToolUse`、`PostToolUse`、`PostToolUseFailure` 和 `PermissionRequest` hooks
- setup 输出运行时 activation 状态：`active`、`needs_reload` 或 `not_in_claude_code`，用于区分 settings 已配置与当前 Claude Code 会话 hooks 已激活
- `lumiagent setup claude-code --verify` 只检查 activation，不修改 settings
- 当 activation 为 `needs_reload` 时，用户应打开 `/hooks` 后关闭，或重启 Claude Code，再触发任意工具调用并重新 verify
- hooks 将工具调用事件写入 `.lumiagent/sessions/<session-id>/events.jsonl`（LumiAgent 自定义格式）
- `lumiagent trace <session-id> -o trace.json` 将事件转为 AgentRun
- 可选：从 Claude Code 会话转录中补充用户消息和 LLM 推理内容
- 稳定性仅依赖 hooks 触发（Claude Code 文档化的产品功能），不依赖内部转录格式

织入 — 真实案例 fixture：

- 通过 hooks 采集流程从真实 Claude Code 会话生成至少一个 trace fixture
- 同时作为测试产物和演示素材

织入 — 最小 CLI Viewer：

- `lumiagent show <trace.json>` 在终端打印 span tree 和 diagnosis summary
- 定位为开发辅助工具，非产品功能

验收标准：

- 可以表达一次 Coding Agent 从需求到验证的完整执行链路
- 可以识别修改代码但未测试、命令失败未处理等流程问题
- 真实 Claude Code 会话可以通过 hooks 采集并转为合法 AgentRun
- hook setup 可以暴露当前会话是 `active`、`needs_reload` 还是 `not_in_claude_code`，并记录 `needs_reload` 时的 `/hooks` 热加载路径
- trace 可在 CLI Viewer 中查看

### Phase 4: Evaluation / Diagnosis Engine

目标：建立评测与诊断引擎，以 Diagnosis Agent 形式实现，基于 LumiAgent 自身的 Agent 基础设施（ReActEngine、ToolRegistry、RAGPipeline、MemoryManager）。

交付物：

- Diagnosis Agent，配备专用 system prompt 和推理策略
- trace 分析专用工具集：`read_span_tree`、`inspect_span`、`extract_evidence`、`query_knowledge`、`compare_arguments`、`check_workflow_pattern`、`compare_traces`
- 规则引擎层，作为快速预检工具（确定性检查，无需 LLM）
- LLM 推理层，通过 ReAct 循环进行多步分析
- 初始评估规则集，加载到 RAGPipeline
- `KnowledgeProvider` 接口，为未来专家知识库扩展预留
- diagnosis report schema

验收标准：

- Diagnosis Agent 可以接收 trace.json，通过 ReAct 循环分析，产出包含 score、reason、evidence_span_ids 和 suggested_fix 的 Evaluation 与 Diagnosis 记录
- 可以定位至少三类失败：上下文不足、工具误用（含 MCP 参数错误）、验证缺失
- Diagnosis Agent 自身执行过程可被 trace 捕获（dogfooding）
- 评测结果包含 score、reason、evidence span 和 suggested fix
- 至少一个端到端示例：Phase 3 产出的真实 trace → Diagnosis Agent → 结构化诊断报告

### Phase 5: Replay / Visualization Preparation

目标：为后续 UI 可视化准备稳定数据接口。

交付物：

- trace replay view model
- timeline data model
- span detail data model
- diagnosis summary data model
- CLI Viewer 升级为消费 view model 的正式版本（基础版在 Phase 2b 创建）
- trace diff 视图：`lumiagent diff trace1.json trace2.json` 用于对比成功和失败的 run
- Experiment 容器模型：将多个 Run 组织在一起进行横向评估

验收标准：

- 不依赖具体 UI 框架即可输出 replay 所需数据
- 可以从同一份 trace 生成 timeline、span tree、detail 和 diagnosis summary
- view model 可支撑 Diagnosis Agent 报告的渲染（包括 evaluation 和 diagnosis，不仅是 span tree）
- 同一任务的两个 trace 可以进行结构化对比，突出差异 span

## 7. 扩展点预留

以下扩展点在当前阶段完成设计，后续阶段实现。确保未来功能可以在不破坏 Core 的前提下构建。

### 7.1 多 Agent Run 关联

为 `AgentRun` 新增可选字段：

- `parent_run_id: Optional[str]` — 触发本次 run 的父 run
- `triggered_by_span_id: Optional[str]` — 父 run 中触发本次 run 的 span

Phase 3-5 不使用这两个字段，但 schema 和序列化必须支持。

### 7.2 Span 级别序列化

确保 serializer 支持单 Span 的 `to_dict` / `from_dict`，不强制整个 Run 一次性序列化。为未来流式 trace writer 和增量 append 预留能力。

Phase 3 的 hooks 采集天然是逐事件写入的，该扩展点确保模型层能表达增量构建的 trace。

### 7.3 TraceWriter 协议

定义 `TraceWriter` 接口：

- `start_run()`
- `start_span()`
- `end_span()`
- `add_event()`
- `add_artifact()`
- `flush()`

Phase 3 的 hooks converter 是该接口的第一个消费者。未来 SDK decorator、MCP proxy 和其他 Agent 框架适配器均实现此接口。

### 7.4 Annotation 模型

定义 `Annotation` 模型，用于人工对 trace 的标注反馈。结构类似 `Evaluation`，但来源是人工审核而非自动化 Agent。

标注数据形成反馈飞轮：

- 为衡量 Diagnosis Agent 准确率提供 ground truth
- 为专家知识库（Phase 8）提供训练素材（annotation → knowledge rule）
- 随着使用量增加实现有监督评估

Phase 3-5 不实现完整标注工作流，但 Core 中应预留 Annotation 模型，与 Evaluation 和 Diagnosis 并列。

### 7.5 隐私脱敏管线

在 `CaptureStrategy` 管线中定义可选的脱敏接口。真实 Agent 的 trace 可能包含源代码、API key、credentials 等敏感数据。

脱敏层在存储或分享前对敏感内容进行剥离或掩码。Phase 2b-5 不实现完整脱敏，但管线挂载点应存在，使各 `CaptureStrategy` 实现可以选择性接入。

## 8. 未来阶段

未来阶段仅描述目标和依赖关系。详细交付物和验收标准在各阶段正式启动时定义。

### Phase 6: 采集 SDK + MCP Proxy

目标：提供完整的 Python SDK（decorator / context manager）用于 Agent 代码插桩，以及 MCP 流量代理用于透明捕获 MCP 工具链数据。

依赖：Phase 3 TraceWriter 接口。

### Phase 7: Web UI

目标：基于浏览器的 trace timeline、span tree 和 diagnosis report 可视化。

依赖：Phase 5 view model。

### Phase 8: 专家知识库 + 高级诊断

目标：基于真实 case 积累的领域知识库，增强 Diagnosis Agent 的 RAG 能力和诊断深度。

依赖：Phase 4 KnowledgeProvider 接口。

### Phase 9: 多 Agent 可视化 + 性能优化

目标：跨 Run trace linking、大 trace 流式处理、span 采样和压缩策略。

依赖：第 7 节扩展点。

## 9. 阶段性验收要求

每个阶段必须满足：

1. 有明确需求说明
2. 有架构或模型设计
3. 有代码实现
4. 有测试或可执行验证
5. 有示例数据或最小 demo
6. 有阶段总结，说明是否偏离核心定位

未经验证，不得宣称阶段完成。

扩展点（第 7 节）通过 schema 级测试验证：字段存在、序列化往返正确、接口可导入。

未来阶段（第 8 节）在实现前需先完成各自的正式规格文档。

## 10. 测试与验证策略

测试必须贯穿整个项目：

- 核心模型使用单元测试
- 序列化格式使用快照或结构校验测试
- 示例 trace 使用集成测试
- evaluator 使用可重复的 fixture 测试
- CLI 或 demo 使用端到端验证
- 真实 trace 验证（Phase 2b 起）：从真实 MCP Server 交互和 Claude Code 会话采集的 trace 必须能校验为合法 AgentRun 对象

测试重点不是覆盖率数字，而是真实证明 LumiAgent 能表达、回放、评测和诊断 Agent 工作流。

## 11. 架构原则

- Trace 是一等公民
- Core 与 Adapter 分离
- 数据模型优先于 UI；当数据模型稳定时，UI 需要友好且优雅
- 评测结果必须能追溯到 evidence span
- Coding Agent / MCP 是首个落地场景，不应污染通用 Core
- 兼容未来 SDK、hooks、MCP proxy、CLI wrapper、transcript importer 等采集方式
- 采集层与模型层解耦：trace 的产生方式（hooks / SDK / proxy / importer）不应影响 Core 数据模型
- 评估结果由 Agent 产生：诊断和评估通过 Diagnosis Agent 的结构化推理生成，而非仅靠硬编码规则
- 自身可观测：LumiAgent 的 Diagnosis Agent 自身执行过程应可被 trace 捕获（dogfooding）

## 12. 功能取舍标准

新增功能必须回答：

1. 是否服务于 Trace / Eval Core？
2. 是否增强 Coding Agent 或 MCP Tool Chain 场景？
3. 是否能改善轨迹回放、评测或诊断？
4. 是否有明确验收方式？
5. 是否会把项目带向泛化 LLM observability 或大而全 Agent framework？

如果答案不能支持当前主线，应暂缓实现。
