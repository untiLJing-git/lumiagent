# LumiAgent 项目规格说明

## 1. 核心定位

LumiAgent 是一个通用 Agent Trace / Eval Core，将 LLM、Tool、RAG、Memory、Evaluator、Fallback、Error 等执行节点统一建模为可嵌套的 Span Tree，使 Agent Run 可以被结构化记录、逐步回放、指标评测和失败归因。

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

目标不是简单“支持 MCP”，而是看清 Agent 如何使用 MCP 工具链，以及工具链失败发生在哪一层。

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

## 6. MVP 阶段规划

### Phase 1: Trace Schema / Span Tree Core

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

### Phase 2: MCP Tool Chain Model

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

### Phase 3: Coding Agent Trace Model

目标：建立 Coding Agent 执行轨迹模型。

交付物：

- file_search / file_read / code_edit / shell_command / test_run / git_diff span
- 一次 coding task 的完整示例 trace
- 基础 workflow validator

验收标准：

- 可以表达一次 Coding Agent 从需求到验证的完整执行链路
- 可以识别修改代码但未测试、命令失败未处理等流程问题

### Phase 4: Evaluation / Diagnosis Engine

目标：建立最小评测与诊断闭环。

交付物：

- context gathering evaluator
- tool use evaluator
- verification evaluator
- risk evaluator
- diagnosis report schema

验收标准：

- 可以对示例 Coding Agent trace 生成评测结果
- 评测结果包含 score、reason、evidence span 和 suggested fix
- 可以定位至少三类失败：上下文不足、工具误用、验证缺失

### Phase 5: Replay / Visualization Preparation

目标：为后续 UI 可视化准备稳定数据接口。

交付物：

- trace replay view model
- timeline data model
- span detail data model
- diagnosis summary data model

验收标准：

- 不依赖具体 UI 框架即可输出 replay 所需数据
- 可以从同一份 trace 生成 timeline、span tree、detail 和 diagnosis summary

## 7. 阶段性验收要求

每个阶段必须满足：

1. 有明确需求说明
2. 有架构或模型设计
3. 有代码实现
4. 有测试或可执行验证
5. 有示例数据或最小 demo
6. 有阶段总结，说明是否偏离核心定位

未经验证，不得宣称阶段完成。

## 8. 测试与验证策略

测试必须贯穿整个项目：

- 核心模型使用单元测试
- 序列化格式使用快照或结构校验测试
- 示例 trace 使用集成测试
- evaluator 使用可重复的 fixture 测试
- CLI 或 demo 使用端到端验证

测试重点不是覆盖率数字，而是真实证明 LumiAgent 能表达、回放、评测和诊断 Agent 工作流。

## 9. 架构原则

- Trace 是一等公民
- Core 与 Adapter 分离
- 数据模型优先于 UI
- 评测结果必须能追溯到 evidence span
- Coding Agent / MCP 是首个落地场景，不应污染通用 Core
- 兼容未来 SDK、hooks、MCP proxy、CLI wrapper、transcript importer 等采集方式

## 10. 功能取舍标准

新增功能必须回答：

1. 是否服务于 Trace / Eval Core？
2. 是否增强 Coding Agent 或 MCP Tool Chain 场景？
3. 是否能改善轨迹回放、评测或诊断？
4. 是否有明确验收方式？
5. 是否会把项目带向泛化 LLM observability 或大而全 Agent framework？

如果答案不能支持当前主线，应暂缓实现。
