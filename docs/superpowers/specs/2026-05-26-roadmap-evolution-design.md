# Roadmap Evolution Design

Date: 2026-05-26

## Context

LumiAgent has completed Phase 1 (Trace Core MVP) and Phase 2 (MCP Tool Chain Model). The existing roadmap covers Phase 1-5 as data-model-centric work. Analysis revealed that the product needs three additional layers to move from a schema library to a usable observability tool:

1. A real capture/ingestion layer with stable, user-friendly agent integration.
2. A UI/interaction layer for viewing and exploring traces.
3. An expert-knowledge-driven evaluation/diagnosis layer with full Agent capabilities.

This design describes how to weave these needs into the existing roadmap without breaking the current rhythm, while preserving extensibility for future phases.

## Decision: Approach B (Layered Restructure)

PROJECT_SPEC is restructured from 10 sections to 12 sections. Sections 1-5 (positioning, background, product line, non-goals, core modules) remain unchanged. The MVP phases section is enhanced in place, a new Extension Points section is added, and a new Future Phases section is added. Existing sections 7-10 are renumbered to 9-12.

| Section | Before | After |
|---------|--------|-------|
| 1-5 | Positioning / Background / Product Line / Non-Goals / Core Modules | Unchanged |
| 6 | MVP Phases (Phase 1-5 flat) | Renamed: MVP Phases (Near-term), Phase 3-5 enhanced |
| 7 | Staged Acceptance | New: Extension Points |
| 8 | Testing Strategy | New: Future Phases (Phase 6-9) |
| 9 | Architecture Principles | Renumbered from old section 7 |
| 10 | Feature Selection Rules | Renumbered from old section 8 |
| 11 | — | Renumbered from old section 9, with additions |
| 12 | — | Renumbered from old section 10 |

## Phase 2 Split: 2a (Model) + 2b (Capture + Display)

Phase 2 is split into two sub-phases:

- **Phase 2a: MCP Tool Chain Model — completed.** The data model, builder helpers, taxonomy, and hand-crafted fixtures.
- **Phase 2b: MCP Capture + Display Chain — new.** Closes the minimal capture-model-display loop for MCP traces before Phase 3.

### Unified Capture Entry Point

Phase 2b establishes a `CaptureStrategy` protocol (strategy pattern) as the shared entry point for all capture methods:

```text
CaptureStrategy
├── McpCaptureStrategy          (Phase 2b)
├── ClaudeCodeHooksStrategy     (Phase 3)
├── TranscriptImportStrategy    (future)
├── SdkDecoratorStrategy        (Phase 6)
└── McpProxyStrategy            (Phase 6)
```

Each strategy's detailed capture mechanism is defined when that strategy is implemented.

### Phase 2b Deliverables

- `CaptureStrategy` protocol definition
- `McpCaptureStrategy`: programmatically calls a real MCP server, records the full chain (connection, discovery, schema, call, result) using Phase 2a builder helpers
- `lumiagent capture mcp <args> -o trace.json` CLI command
- Minimal MCP trace CLI viewer: `lumiagent show <trace.json>` prints MCP span tree, failure types, and evidence fields
- At least one trace from a real MCP server interaction

### Phase 2b Acceptance Criteria

- A real MCP server interaction can be captured and converted to a valid AgentRun.
- The trace can be viewed with `lumiagent show`, displaying MCP-specific information.
- The `CaptureStrategy` protocol is defined and extensible.

## Phase 3 Enhancement: Real Capture Integration

Phase 3 original deliverables (Coding Agent span types, complete example trace, workflow validator) remain. The following are woven in:

### Claude Code Hooks Capture

Target agent: Claude Code (aligns with Coding Agent + MCP positioning).

Capture method: Claude Code hooks system (documented product feature). The approach avoids parsing internal `.jsonl` transcripts. Instead, hooks write events in a format defined by LumiAgent.

User experience:

1. `lumiagent setup claude-code` — one-time setup, registers hooks in `.claude/settings.json`.
2. User runs Claude Code normally — hooks write tool use events to `.lumiagent/sessions/<session-id>/events.jsonl` (our format).
3. `lumiagent trace <session-id> -o trace.json` — converts events to AgentRun.
4. Optional: enrich from Claude Code session transcripts (user messages, LLM reasoning) when available.

Stability: depends only on hooks firing (documented feature), not on internal transcript format. The intermediate `events.jsonl` format is defined and controlled by LumiAgent.

### Real Case Fixture

Use the hooks capture flow to generate at least one trace fixture from a real Claude Code session. This fixture serves as both a test artifact and demo material.

### Minimal CLI Viewer

`lumiagent show <trace.json>` — prints span tree and diagnosis summary in the terminal. Positioned as a developer tool, not a product feature. Estimated scope: ~200 lines.

### Updated Acceptance Criteria

A real Claude Code session can be captured via hooks and converted to a valid AgentRun viewable in the CLI viewer.

## Phase 4 Enhancement: Diagnosis Agent

Phase 4 original deliverables (context/tool/verification/risk evaluators, diagnosis report schema) are reframed. The evaluation/diagnosis engine is a Diagnosis Agent built on LumiAgent's own agent infrastructure.

### Architecture

| Component | Reuse | New |
|-----------|-------|-----|
| Agent engine | ReActEngine (or Plan-and-Solve variant) | Diagnosis-specific system prompt and reasoning strategy |
| Tools | ToolRegistry + BaseTool interface | Trace analysis tool set |
| Knowledge retrieval | RAGPipeline | Evaluation rules, best practices, failure pattern content |
| Memory | MemoryManager (short-term) | Finding accumulation during evaluation |
| Output | Trace Core Evaluation + Diagnosis models | Structured diagnosis report generation |

### Trace Analysis Tools

- `read_span_tree` — trace structure overview
- `inspect_span` — deep read of a span's input/output/artifacts/events
- `extract_evidence` — evidence chain extraction for a suspected failure
- `query_knowledge` — search evaluation rules and best practices
- `compare_arguments` — compare tool arguments against schema
- `check_workflow_pattern` — verify workflow follows expected patterns (e.g. edit followed by test)
- `compare_traces` — compare a successful and failed run of the same task to identify divergent decisions

### Three-Layer Evaluation

| Layer | Phase 4 scope |
|-------|--------------|
| Rule engine | Implemented as fast pre-check tools for the Diagnosis Agent (deterministic, no LLM needed) |
| LLM reasoning | The Diagnosis Agent itself, using ReAct for multi-step analysis |
| Expert knowledge base | RAGPipeline with initial evaluation rule set; `KnowledgeProvider` interface defined for future expansion |

### Dogfooding

The Diagnosis Agent's own execution is captured as an AgentRun trace. The CLI viewer can show how the agent reached its conclusions.

### Updated Acceptance Criteria

- Diagnosis Agent accepts a trace.json, analyzes it via ReAct loop, produces Evaluation and Diagnosis records with score / reason / evidence_span_ids / suggested_fix.
- Can diagnose at least three failure types: insufficient context, tool misuse (including MCP argument errors), insufficient verification.
- Agent's own execution can be trace-captured.

## Phase 5 Adjustment

Original deliverables (replay view model, timeline, span detail, diagnosis summary data model) remain. Adjustments:

- CLI Viewer (basic version from Phase 2b) is upgraded to consume view models.
- View models must support rendering Diagnosis Agent reports (evaluations and diagnoses, not only span trees).
- Trace diff view: `lumiagent diff trace1.json trace2.json` CLI command for comparing successful and failed runs, highlighting divergent spans.
- Experiment container model activated: groups multiple Runs for comparative evaluation.

## New Section 7: Extension Points

Five extension points to be designed now and implemented later.

### 7.1 Multi-Agent Run Linking

Add to `AgentRun`:
- `parent_run_id: Optional[str]`
- `triggered_by_span_id: Optional[str]`

Phase 3-5 do not use these fields, but schema and serialization must support them.

### 7.2 Span-Level Serialization

Ensure serializer supports single-Span `to_dict` / `from_dict`, not only whole-Run serialization. Enables future streaming writer and incremental append. Phase 3 hooks capture is naturally per-event, so this extension point ensures seamless future integration.

### 7.3 TraceWriter Protocol

Define a `TraceWriter` interface: `start_run()` / `start_span()` / `end_span()` / `add_event()` / `add_artifact()` / `flush()`. Phase 3 hooks converter is the first consumer. Future SDK decorators, MCP proxy, and other agent framework adapters implement this interface.

### 7.4 Annotation Model

An `Annotation` model is added to Core alongside Evaluation and Diagnosis. Annotations capture human feedback on traces ("this span was a wrong decision", "this was correct"). This creates a feedback flywheel:

- Ground truth for measuring Diagnosis Agent accuracy.
- Training material for the expert knowledge base (Phase 8).
- Supervised evaluation over time.

Phase 3-5 define the model but do not implement annotation workflows.

### 7.5 Privacy Sanitization Pipeline

A sanitization interface is defined as an optional step in the `CaptureStrategy` pipeline. Real traces may contain source code, API keys, or credentials. The hook point exists so capture strategies can opt into sanitization before storage or sharing.

## New Section 8: Future Phases

| Phase | Name | Goal | Depends on |
|-------|------|------|-----------|
| 6 | Capture SDK + MCP Proxy | Full Python SDK (decorator / context manager) + MCP traffic proxy capture | Phase 3 TraceWriter interface |
| 7 | Web UI | Browser-based trace timeline, span tree, diagnosis report visualization | Phase 5 view models |
| 8 | Expert Knowledge Base + Advanced Diagnosis | Domain knowledge base built from real cases, enhancing Diagnosis Agent RAG capability | Phase 4 KnowledgeProvider interface |
| 9 | Multi-Agent Visualization + Performance | Cross-run trace linking, large trace streaming, span sampling/compression | Section 7 extension points |

Future phases describe goals and dependencies only. Detailed deliverables and acceptance criteria are defined when each phase begins.

## Architecture Principles Additions

Three new principles added to existing set:

- Data models before UI; when data models are stable, UI should be friendly and elegant (updated from original "prioritize data models before UI").
- Capture layer decoupled from model layer: how traces are produced (hooks / SDK / proxy / importer) must not affect the Core data model.
- Evaluation results produced by Agent: diagnosis and evaluation are generated through Diagnosis Agent's structured reasoning, not hardcoded rules.
- Self-observable: LumiAgent's Diagnosis Agent execution must itself be trace-capturable (dogfooding).

## Additional Notes

### Core Modules Update

`Annotation` is added to the Core Modules entity list (§5.1) alongside Evaluation and Diagnosis.

### Testing: Real Trace Validation from Phase 2b

Real-trace validation starts from Phase 2b (not Phase 3). Traces captured from real MCP server interactions must validate as AgentRun objects. Phase 3 extends this to Claude Code sessions.

## Files to Update

1. `docs/PROJECT_SPEC.md` — restructure to 12 sections, enhance Phase 3-5, add sections 7-8.
2. `docs/PROJECT_SPEC.zh-CN.md` — same changes in Chinese.
3. `README.md` / `README.zh-CN.md` — update roadmap section only.
