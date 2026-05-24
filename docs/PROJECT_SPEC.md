# LumiAgent Project Specification

## 1. Core Positioning

LumiAgent is a general Agent Trace / Eval Core that models LLM, Tool, RAG, Memory, Evaluator, Fallback, and Error steps as a nested Span Tree. It makes each Agent Run structured, replayable, evaluable, and diagnosable.

Its first application focuses on Coding Agents and MCP Tool Chains. LumiAgent captures file search, code reading, code edits, command execution, test verification, MCP tool discovery, tool calls, argument generation, and tool results to diagnose context gaps, tool misuse, argument errors, result misinterpretation, insufficient verification, failure recovery issues, and risk-control problems. The goal is to optimize the overall Coding Agent workflow.

## 2. Background

The market already has mature products such as LangSmith, Langfuse, Phoenix, AgentOps, Braintrust, Helicone, and LangGraph Studio. Generic LLM tracing, prompt management, dataset evaluation, RAG evaluation, and agent session observability are already well-covered.

Therefore, LumiAgent should not be positioned as a generic LLM observability platform or an open-source clone of LangSmith or Langfuse. LumiAgent's differentiation should come from:

- Coding Agent execution trace modeling
- MCP Tool Chain observability and diagnosis
- Evaluation systems for Coding Agent workflows
- AI Profiling-inspired Timeline / Span / Failure Diagnosis experiences

## 3. Current Product Line

LumiAgent currently focuses on four product lines:

1. General Agent Trace / Eval Core
2. Coding Agent Trace
3. MCP Tool Chain Observability
4. Agent Evaluation / Diagnosis

The general Core defines the foundational models: Run, Span, Event, Artifact, Evaluation, Diagnosis, and related entities. Coding Agent and MCP Tool Chain support are the first application and adapter layers built on top of the Core.

## 4. Non-Goals

At the current stage, LumiAgent is not intended to become:

- A generic LLM observability dashboard
- A prompt management platform
- A generic RAG evaluation platform
- A large all-purpose Agent framework
- A generic multi-agent orchestration framework
- A replacement clone of LangSmith, Langfuse, Phoenix, or AgentOps

These capabilities may exist as supporting infrastructure, but they must not become the main product direction.

## 5. Core Modules

### 5.1 Trace / Eval Core

Defines the general execution data model for Agent systems:

- Agent Run
- Span Tree
- Event
- Artifact
- Evaluation
- Diagnosis
- Experiment

Core requirements:

- Framework-agnostic
- Nestable
- Serializable
- Replayable
- Evaluable
- Extensible to different Agent frameworks and tool protocols

### 5.2 Coding Agent Trace

Models Coding Agent execution workflows:

- user_prompt
- file_search
- file_read
- code_edit
- shell_command
- test_run
- browser_verify
- git_diff
- final_response

The goal is to explain how a Coding Agent understands a task, gathers context, edits code, verifies changes, and handles failures.

### 5.3 MCP Tool Chain Observability

Models and diagnoses MCP tool chains:

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

The goal is not merely to "support MCP", but to make it clear how an Agent uses MCP tools and where tool-chain failures occur.

### 5.4 Evaluation / Diagnosis

Provides evaluation and diagnosis for Agent workflows:

- context gathering diagnosis
- tool selection diagnosis
- tool argument diagnosis
- tool result faithfulness
- verification sufficiency
- failure recovery diagnosis
- risk control diagnosis

Evaluation output should include:

- score
- reason
- evidence span
- failure type
- suggested fix

## 6. MVP Phases

### Phase 1: Trace Schema / Span Tree Core

Goal: establish LumiAgent's core data model.

Deliverables:

- Run / Span / Event / Artifact / Evaluation / Diagnosis models
- JSON serialization
- Basic unit tests
- Example trace data

Acceptance criteria:

- A simple Agent Run can be represented as a unified Span Tree.
- The trace can be serialized into stable JSON.
- Tests cover core model creation, nesting, and serialization.

### Phase 2: MCP Tool Chain Model

Goal: establish the MCP tool-chain observability model.

Deliverables:

- MCP server / tool discovery / tool call / tool result spans
- tool schema and argument record structures
- error / latency / permission fields
- example MCP tool-chain trace

Acceptance criteria:

- A full MCP flow from tool discovery to tool result can be represented.
- Tool arguments, results, errors, and latency can be recorded.
- Tool-call failure types can be identified.

### Phase 3: Coding Agent Trace Model

Goal: establish the Coding Agent execution trace model.

Deliverables:

- file_search / file_read / code_edit / shell_command / test_run / git_diff spans
- complete example trace for a coding task
- basic workflow validator

Acceptance criteria:

- A Coding Agent workflow from user request to verification can be represented.
- Process issues such as editing code without tests or ignoring failed commands can be identified.

### Phase 4: Evaluation / Diagnosis Engine

Goal: establish the minimal evaluation and diagnosis loop.

Deliverables:

- context gathering evaluator
- tool use evaluator
- verification evaluator
- risk evaluator
- diagnosis report schema

Acceptance criteria:

- Example Coding Agent traces can produce evaluation results.
- Results include score, reason, evidence span, and suggested fix.
- At least three failure types can be diagnosed: context gaps, tool misuse, and insufficient verification.

### Phase 5: Replay / Visualization Preparation

Goal: prepare stable data interfaces for future UI visualization.

Deliverables:

- trace replay view model
- timeline data model
- span detail data model
- diagnosis summary data model

Acceptance criteria:

- Replay data can be produced without depending on a specific UI framework.
- The same trace can generate timeline, span tree, detail, and diagnosis summary views.

## 7. Staged Acceptance Requirements

Each phase must include:

1. Clear requirements
2. Architecture or model design
3. Code implementation
4. Tests or executable verification
5. Example data or a minimal demo
6. A phase summary explaining whether the work still aligns with the core positioning

A phase must not be marked complete without verification.

## 8. Testing and Verification Strategy

Testing must run throughout the project:

- Unit tests for core models
- Snapshot or structural validation tests for serialization formats
- Integration tests for example traces
- Repeatable fixture tests for evaluators
- End-to-end verification for CLI or demos

The goal is not a superficial coverage number. Tests must prove that LumiAgent can represent, replay, evaluate, and diagnose Agent workflows.

## 9. Architecture Principles

- Treat traces as first-class product data.
- Separate Core from Adapters.
- Prioritize data models before UI.
- Evaluation results must be traceable to evidence spans.
- Coding Agent and MCP support are the first application layer and must not pollute the general Core.
- Keep room for future ingestion through SDKs, hooks, MCP proxies, CLI wrappers, and transcript importers.

## 10. Feature Selection Rules

Every new feature must answer:

1. Does it serve the Trace / Eval Core?
2. Does it strengthen the Coding Agent or MCP Tool Chain scenario?
3. Does it improve trace replay, evaluation, or diagnosis?
4. Does it have clear acceptance criteria?
5. Does it risk turning LumiAgent into a generic LLM observability platform or all-purpose Agent framework?

If a feature does not support the current product line, postpone it.
