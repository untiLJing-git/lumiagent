# LumiAgent Project Specification

## 1. Core Positioning

LumiAgent is an Agent Evaluation & Optimization Loop that turns evaluation from a score into a path to improvement. Benchmark scores tell whether an agent succeeded. LumiAgent explains how the run unfolded, where failure emerged, what evidence supports the diagnosis, and which changes are most likely to improve the next run.

Its product loop is:

```text
run tasks → capture traces → diagnose failures → review evidence → apply improvements → compare reruns
```

Under this loop, LumiAgent provides a general Agent Trace / Eval Core that models LLM, Tool, RAG, Memory, Evaluator, Fallback, and Error steps as a nested Span Tree. It makes each Agent Run structured, replayable, evaluable, and diagnosable.

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
- Annotation

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

## 6. MVP Phases (Near-term)

### Phase 1: Trace Schema / Span Tree Core — completed

Goal: establish LumiAgent's core data model.

Formal specification: `docs/specs/trace-core-mvp.md`.

Deliverables:

- Run / Span / Event / Artifact / Evaluation / Diagnosis models
- JSON serialization
- Basic unit tests
- Example trace data

Acceptance criteria:

- A simple Agent Run can be represented as a unified Span Tree.
- The trace can be serialized into stable JSON.
- Tests cover core model creation, nesting, and serialization.

### Phase 2a: MCP Tool Chain Model — completed

Goal: establish the MCP tool-chain observability model as a structured evidence layer for later Coding Agent Trace and Evaluation / Diagnosis work.

Formal specification: `docs/specs/mcp-tool-chain-model.md`.

Deliverables:

- MCP server / tool discovery / tool call / tool result spans
- tool schema and argument record structures
- MCP failure taxonomy and evidence fields
- error / latency / permission fields
- successful and failed example MCP tool-chain traces

Acceptance criteria:

- A full MCP flow from tool discovery to tool result can be represented.
- Tool arguments, results, errors, and latency can be recorded.
- Tool-call failure types can be identified.

### Phase 2b: MCP Capture + Display Chain — completed

Goal: close the minimal capture-model-display loop for MCP traces, and establish the unified capture entry point used by all future capture strategies.

Deliverables:

- `CaptureStrategy` protocol as the unified capture entry point (strategy pattern)
- `McpCaptureStrategy` as the first implementation: programmatically calls a real MCP server, records the full chain (connection, discovery, schema, call, result) using Phase 2a builder helpers
- `lumiagent capture mcp <args> -o trace.json` CLI command
- minimal MCP trace CLI viewer: `lumiagent show <trace.json>` prints MCP span tree, failure types, and evidence fields
- at least one trace generated from a real MCP server interaction

The `CaptureStrategy` protocol is the shared entry point for all future capture methods:

```text
CaptureStrategy
├── McpCaptureStrategy          (Phase 2b)
├── ClaudeCodeHooksStrategy     (Phase 3)
├── TranscriptImportStrategy    (future)
├── SdkDecoratorStrategy        (Phase 6)
└── McpProxyStrategy            (Phase 6)
```

Each strategy's detailed capture mechanism is defined when that strategy is implemented.

Acceptance criteria:

- A real MCP server interaction can be captured and converted to a valid AgentRun.
- The trace can be viewed with `lumiagent show`, displaying MCP-specific information (failure type, schema, arguments, result consumption).
- The `CaptureStrategy` protocol is defined and extensible for future capture methods.

### Phase 3: Coding Agent Trace Model — completed

Goal: establish the Coding Agent execution trace model and validate it against real agent data.

Formal specification: `docs/specs/coding-agent-trace-model.md`.

Technical report: `docs/reports/coding-agent-trace-model-technical-report.zh-CN.md`.

Deliverables:

- file_search / file_read / code_edit / shell_command / test_run / git_diff spans
- complete example trace for a coding task
- basic workflow validator

Woven in — Claude Code hooks capture:

- `lumiagent setup claude-code` one-time setup command that registers `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, and `PermissionRequest` hooks in `.claude/settings.json`
- setup reports runtime activation as `active`, `needs_reload`, or `not_in_claude_code`, so users can distinguish configured settings from hooks that are active in the current Claude Code session
- `lumiagent setup claude-code --verify` checks activation without modifying settings
- when activation is `needs_reload`, users should open `/hooks` and close it, or restart Claude Code, then trigger any tool call and verify again
- hooks write tool use events to `.lumiagent/sessions/<session-id>/events.jsonl` (LumiAgent-defined format)
- `lumiagent trace <session-id> -o trace.json` converts events to AgentRun
- optional enrichment from Claude Code session transcripts (user messages, LLM reasoning) when available
- stability depends only on hooks firing (documented Claude Code feature), not on internal transcript format

Woven in — real case fixture:

- at least one trace fixture generated from a real Claude Code session via the hooks capture flow
- serves as both test artifact and demo material

Woven in — minimal CLI viewer:

- `lumiagent show <trace.json>` prints span tree, semantic summary, and workflow checks in the terminal
- positioned as a developer tool, not a product feature

Acceptance criteria:

- A Coding Agent workflow from user request to verification can be represented.
- Process issues such as editing code without tests or ignoring failed commands can be identified.
- A real Claude Code session can be captured via hooks and converted to a valid AgentRun.
- Hook setup exposes whether the current session is `active`, `needs_reload`, or `not_in_claude_code`, and documents the `/hooks` reload path for `needs_reload` sessions.
- The trace can be viewed in the CLI viewer.

### Phase 4: Evaluation / Diagnosis Engine

Goal: establish the evaluation and diagnosis engine as a Diagnosis Agent built on LumiAgent's own agent infrastructure (ReActEngine, ToolRegistry, RAGPipeline, MemoryManager).

Deliverables:

- Diagnosis Agent with specialized system prompt and reasoning strategy
- trace analysis tool set: `read_span_tree`, `inspect_span`, `extract_evidence`, `query_knowledge`, `compare_arguments`, `check_workflow_pattern`, `compare_traces`
- rule engine layer as fast pre-check tools (deterministic, no LLM)
- LLM reasoning layer via ReAct loop for multi-step analysis
- initial evaluation rule set loaded into RAGPipeline
- `KnowledgeProvider` interface for future expert knowledge base expansion
- diagnosis report schema

Acceptance criteria:

- Diagnosis Agent accepts a trace.json, analyzes via ReAct loop, produces Evaluation and Diagnosis records with score, reason, evidence_span_ids, and suggested_fix.
- At least three failure types can be diagnosed: insufficient context, tool misuse (including MCP argument errors), and insufficient verification.
- The Diagnosis Agent's own execution can be trace-captured (dogfooding).
- Results include score, reason, evidence span, and suggested fix.
- At least one example runs end-to-end: real trace from Phase 3 → Diagnosis Agent → structured diagnosis report.

### Phase 5: Replay / Visualization Preparation

Goal: prepare stable data interfaces for future UI visualization.

Deliverables:

- trace replay view model
- timeline data model
- span detail data model
- diagnosis summary data model
- CLI viewer upgrade to consume view models (basic version created in Phase 2b)
- trace diff view: `lumiagent diff trace1.json trace2.json` for comparing successful and failed runs
- Experiment container model: groups multiple Runs for comparative evaluation

Acceptance criteria:

- Replay data can be produced without depending on a specific UI framework.
- The same trace can generate timeline, span tree, detail, and diagnosis summary views.
- View models support rendering Diagnosis Agent reports (evaluations and diagnoses, not only span trees).
- Two traces of the same task can be structurally compared, highlighting divergent spans.

## 7. Extension Points

These extension points are designed now but implemented later. They ensure future phases can be built without breaking the Core.

### 7.1 Multi-Agent Run Linking

Add optional fields to `AgentRun`:

- `parent_run_id: Optional[str]` — the parent run that triggered this run
- `triggered_by_span_id: Optional[str]` — the span in the parent run that triggered this run

Phase 3-5 do not use these fields, but schema and serialization must support them.

### 7.2 Span-Level Serialization

Ensure serializer supports single-Span `to_dict` / `from_dict`, not only whole-Run serialization. This enables future streaming trace writer and incremental append.

Phase 3 hooks capture is naturally per-event. This extension point ensures the model layer can represent incrementally built traces.

### 7.3 TraceWriter Protocol

Define a `TraceWriter` interface:

- `start_run()`
- `start_span()`
- `end_span()`
- `add_event()`
- `add_artifact()`
- `flush()`

Phase 3 hooks converter is the first consumer of this interface. Future SDK decorators, MCP proxy, and other agent framework adapters implement the same interface.

### 7.4 Annotation Model

Define an `Annotation` model for human feedback on traces. Similar to `Evaluation` but sourced from human reviewers rather than automated agents.

Annotations create a feedback flywheel:

- Provide ground truth for measuring Diagnosis Agent accuracy.
- Feed into the expert knowledge base (Phase 8) as training material.
- Enable supervised evaluation over time.

Phase 3-5 do not implement annotation workflows, but the model should exist in the Core alongside Evaluation and Diagnosis.

### 7.5 Privacy Sanitization Pipeline

Define a sanitization interface as an optional step in the `CaptureStrategy` pipeline. Traces from real agents may contain source code, API keys, credentials, or other sensitive data.

The sanitization layer strips or masks sensitive content before storage or sharing. Phase 2b-5 do not implement full sanitization, but the pipeline hook point should exist so that `CaptureStrategy` implementations can opt in.

## 8. Future Phases

Future phases describe goals and dependencies. Detailed deliverables and acceptance criteria are defined when each phase begins.

### Phase 6: Capture SDK + MCP Proxy

Goal: provide a full Python SDK (decorator / context manager) for instrumenting agent code, and an MCP traffic proxy for transparent MCP tool chain capture.

Depends on: Phase 3 TraceWriter interface.

### Phase 7: Web UI

Goal: browser-based visualization for trace timeline, span tree, and diagnosis reports.

Depends on: Phase 5 view models.

### Phase 8: Expert Knowledge Base + Advanced Diagnosis

Goal: build a domain knowledge base from accumulated real cases to enhance the Diagnosis Agent's RAG capability and diagnostic depth.

Depends on: Phase 4 KnowledgeProvider interface.

### Phase 9: Multi-Agent Visualization + Performance

Goal: cross-run trace linking for multi-agent scenarios, large trace streaming, span sampling, and compression strategies.

Depends on: Section 7 extension points.

## 9. Staged Acceptance Requirements

Each phase must include:

1. Clear requirements
2. Architecture or model design
3. Code implementation
4. Tests or executable verification
5. Example data or a minimal demo
6. A phase summary explaining whether the work still aligns with the core positioning

A phase must not be marked complete without verification.

Extension points (Section 7) are verified through schema-level tests: fields exist, serialization round-trips, interfaces are importable.

Future phases (Section 8) require their own formal specification before implementation begins.

## 10. Testing and Verification Strategy

Testing must run throughout the project:

- Unit tests for core models
- Snapshot or structural validation tests for serialization formats
- Integration tests for example traces
- Repeatable fixture tests for evaluators
- End-to-end verification for CLI or demos
- Real-trace validation (Phase 2b+): traces captured from real MCP server interactions and Claude Code sessions must validate as AgentRun objects

The goal is not a superficial coverage number. Tests must prove that LumiAgent can represent, replay, evaluate, and diagnose Agent workflows.

## 11. Architecture Principles

- Treat traces as first-class product data.
- Separate Core from Adapters.
- Prioritize data models before UI. When data models are stable, UI should be friendly and elegant.
- Evaluation results must be traceable to evidence spans.
- Coding Agent and MCP support are the first application layer and must not pollute the general Core.
- Keep room for future ingestion through SDKs, hooks, MCP proxies, CLI wrappers, and transcript importers.
- Capture layer decoupled from model layer: how traces are produced (hooks / SDK / proxy / importer) must not affect the Core data model.
- Evaluation results produced by Agent: diagnosis and evaluation are generated through Diagnosis Agent structured reasoning, not hardcoded rules alone.
- Self-observable: LumiAgent's own Diagnosis Agent execution must be trace-capturable (dogfooding).

## 12. Feature Selection Rules

Every new feature must answer:

1. Does it serve the Trace / Eval Core?
2. Does it strengthen the Coding Agent or MCP Tool Chain scenario?
3. Does it improve trace replay, evaluation, or diagnosis?
4. Does it have clear acceptance criteria?
5. Does it risk turning LumiAgent into a generic LLM observability platform or all-purpose Agent framework?

If a feature does not support the current product line, postpone it.
