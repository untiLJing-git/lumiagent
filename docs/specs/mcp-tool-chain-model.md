# MCP Tool Chain Model Specification

## 1. Purpose

Phase 2 establishes the MCP Tool Chain Model for LumiAgent. Its purpose is not to build a generic MCP monitoring platform or connect to a real MCP runtime yet. Its purpose is to create a structured evidence layer that explains how an Agent uses MCP tools and where tool-chain failures occur.

This phase focuses on Coding Agents that use MCP tools, while keeping the model compatible with general Agent MCP flows. The MCP evidence layer becomes a foundation for later Coding Agent Trace modeling and Evaluation / Diagnosis.

## 2. Product Value

Coding Agent failures often happen before or around code editing. The Agent may fail because it did not discover the right tool, selected the wrong tool, generated invalid arguments, missed a permission boundary, hit a tool execution error, or misunderstood a successful tool result.

MCP Tool Chain observability gives LumiAgent a way to answer questions such as:

- Which MCP server and tools were available to the Agent?
- What schema did the Agent see when generating arguments?
- Why did the Agent choose one tool instead of another?
- Were the generated arguments valid for the current schema?
- Was a permission or approval step required, granted, or denied?
- Did the tool execute successfully, time out, or return an invalid result?
- Did the Agent correctly consume the tool result, or did it ignore or contradict important fields?

The value is not only recording tool calls. The value is preserving structured evidence that later evaluators can use to explain tool misuse, insufficient verification, result misinterpretation, and workflow risk.

## 3. Relationship to Later Phases

Phase 2 is an evidence layer, not the full Coding Agent workflow model.

```text
Phase 2 MCP Tool Chain Model:
  records local MCP tool-chain evidence

Phase 3 Coding Agent Trace Model:
  consumes MCP evidence inside a full coding task workflow

Phase 4 Evaluation / Diagnosis Engine:
  consumes MCP and Coding Agent evidence to produce scores, reasons, severity, evidence spans, and suggested fixes
```

Phase 2 can record that a tool result was misinterpreted. It does not decide whether the full coding task failed, whether the final answer is correct, or whether the whole workflow was sufficiently verified.

## 4. Goals

- Define MCP tool-chain span conventions on top of the existing Trace Core.
- Preserve Core / Adapter separation.
- Define stable MCP failure taxonomy outside Core.
- Define stable evidence fields that Phase 4 evaluators can consume.
- Define lightweight schema structures for important MCP artifacts and evidence.
- Define successful and failed example trace fixtures.
- Prepare the module boundary for future MCP SDK integration without implementing runtime capture in this phase.

## 5. Non-goals

Phase 2 does not include:

- Real MCP SDK or MCP Server integration.
- MCP client hooks or server proxy implementation.
- UI, dashboard, or visualization.
- A full automatic diagnosis engine.
- A full Coding Agent workflow model.
- Changes to the Core tracing model unless explicitly justified.
- MCP-specific fields on `AgentRun`, `Span`, `Event`, `Artifact`, `Evaluation`, or `Diagnosis`.
- Large numbers of MCP-specific `SpanKind` or `ArtifactKind` enum values.

## 6. Architecture Boundary

MCP support is an adapter/convention layer over the generic Trace Core.

Recommended module location:

```text
src/lumiagent/adapters/mcp/
  __init__.py
  taxonomy.py
  schemas.py
  conventions.py
  builder.py
```

Responsibilities:

- `taxonomy.py`: `McpFailureType` and related stable failure constants.
- `schemas.py`: lightweight structures for artifact content and evidence payloads.
- `conventions.py`: centralized `metadata.type` and artifact type names.
- `builder.py`: helper functions around `TraceBuilder` that construct standard MCP spans, artifacts, and metadata.

The `src/lumiagent/tracing/` package remains the framework-agnostic Core.

## 7. Recommended MCP Span Tree

Recommended full structure:

```text
mcp_tool_chain span
├── mcp_connection span
├── mcp_discovery span
│   └── mcp_tool_schema_snapshot artifact
├── mcp_tool_selection span optional
├── mcp_argument_generation span optional
├── mcp_permission span optional
├── mcp_tool_execution span
│   ├── input: tool arguments and schema reference
│   ├── artifact: tool result
│   └── output: compact execution summary
└── mcp_result_consumption span
```

### 7.1 SpanKind Mapping

Aggregation and process spans use generic custom spans:

```text
kind = SpanKind.CUSTOM
metadata.type = "mcp_tool_chain"
metadata.type = "mcp_connection"
metadata.type = "mcp_discovery"
metadata.type = "mcp_tool_selection"
metadata.type = "mcp_argument_generation"
metadata.type = "mcp_permission"
metadata.type = "mcp_result_consumption"
```

Actual tool execution uses a tool span:

```text
kind = SpanKind.TOOL
metadata.type = "mcp_tool_execution"
```

This keeps the Core enum stable while still making MCP semantics machine-readable.

### 7.2 Optional Span Compression

`mcp_tool_selection`, `mcp_argument_generation`, and `mcp_permission` are optional spans.

Simple traces may compress their evidence into `mcp_tool_execution.input`, `metadata`, or events. When a failure relates to selection, argument generation, or permission, the trace should prefer an explicit span so future evaluators have clear evidence span IDs.

Retry, fallback, and recovery are not primary Phase 2 MCP objects. They may be represented with generic events or spans when present, such as `retry_attempted` events or `SpanKind.FALLBACK` spans. A future workflow recovery layer can standardize these across MCP, LLM, RAG, shell, browser, and other tool use.

## 8. Data Placement Rules

### 8.1 Tool Schema Snapshot

Tool schema snapshots should be stored as artifacts, not span metadata.

```text
artifact.kind = ArtifactKind.CUSTOM
artifact.metadata.type = "mcp_tool_schema_snapshot"
artifact.content = {
  "server_name": "...",
  "captured_at": "...",
  "schema_version": "...",
  "tools": [...]
}
```

### 8.2 Tool Arguments

Generated or normalized tool arguments should be stored in `mcp_tool_execution.input`.

```text
input = {
  "server_name": "...",
  "tool_name": "...",
  "schema_artifact_id": "...",
  "arguments": {...},
  "validation": {
    "status": "valid | invalid | skipped",
    "errors": [...]
  }
}
```

### 8.3 Tool Result

Tool results should be stored as artifacts because they may be large or structured.

```text
artifact.kind = ArtifactKind.TOOL_RESULT
artifact.metadata.type = "mcp_tool_result"
artifact.content = {...}
```

`mcp_tool_execution.output` should contain only a compact execution summary:

```text
output = {
  "status": "success | error",
  "latency_ms": 123,
  "result_artifact_id": "...",
  "failure_type": "..."
}
```

### 8.4 Result Consumption Evidence

`mcp_result_consumption` records how the Agent used the tool result. The first version uses medium-granularity evidence:

```text
consumed_artifact_ids: list[string]
consumption_summary: string
claimed_facts: list[string]
contradicted_fields: list[string]
ignored_key_fields: list[string]
confidence: float | null
notes: string
```

This supports `result_misinterpreted` without implementing a full evaluator.

## 9. Failure Taxonomy

MCP failure types should be defined outside Core, preferably as `McpFailureType` in `src/lumiagent/adapters/mcp/taxonomy.py`.

Initial taxonomy:

```text
connection_failed
discovery_failed
tool_not_found
schema_unavailable
schema_mismatch
tool_selection_wrong
argument_generation_failed
argument_invalid
permission_required
permission_denied
tool_execution_failed
tool_timeout
tool_result_invalid
result_misinterpreted
insufficient_recovery_evidence
```

These values may be used in MCP metadata, artifacts, events, and later `Diagnosis.failure_type` strings. They must not be added to the generic Core as a required enum.

## 10. Evidence Fields

Each failure type should map to stable evidence. Recommended evidence fields:

```text
failure_type
failure_stage
server_name
tool_name
schema_artifact_id
call_span_id
result_artifact_id
evidence_span_ids
expected
actual
validation_errors
error_code
error_message
latency_ms
permission_status
consumed_artifact_ids
contradicted_fields
ignored_key_fields
notes
```

Examples:

```text
argument_invalid:
  schema_artifact_id + generated arguments + validation_errors + call_span_id

tool_selection_wrong:
  available tools + selected tool + rejected alternatives + selection_reason

permission_denied:
  permission_status + denied_reason + related tool execution span

tool_execution_failed:
  error_code + error_message + latency_ms + call_span_id

result_misinterpreted:
  result_artifact_id + consumed_artifact_ids + claimed_facts + contradicted_fields + ignored_key_fields
```

Phase 2 records evidence. Phase 4 decides score, severity, reason, and suggested fix.

## 11. Lightweight Schemas

The implementation should prefer small schema structures over a large MCP framework. Suggested schemas:

```text
McpToolSchemaSnapshot
McpToolCallInput
McpToolExecutionSummary
McpFailureEvidence
McpResultConsumptionEvidence
```

These schemas should validate the shape of artifact content and evidence payloads used by helpers and fixtures. They should not replace the generic Trace Core models.

## 12. Helper API Direction

Suggested helper functions:

```text
start_mcp_tool_chain(...)
add_mcp_connection(...)
add_mcp_discovery(...)
add_mcp_tool_schema_snapshot(...)
add_mcp_tool_execution(...)
add_mcp_tool_result(...)
add_mcp_failure_evidence(...)
add_mcp_result_consumption(...)
```

Helpers should construct standard `Span`, `Artifact`, `input`, `output`, and `metadata` payloads through the existing `TraceBuilder`. They should not connect to a real MCP SDK in Phase 2.

## 13. Required Fixtures

Phase 2 should include at least four example trace fixtures:

```text
tests/adapters/mcp/fixtures/mcp_success_trace.json
tests/adapters/mcp/fixtures/mcp_argument_invalid_trace.json
tests/adapters/mcp/fixtures/mcp_tool_execution_failed_trace.json
tests/adapters/mcp/fixtures/mcp_result_misinterpreted_trace.json
```

Coverage:

- `mcp_success_trace.json`: successful connection, discovery, schema snapshot, tool execution, result artifact, and result consumption.
- `mcp_argument_invalid_trace.json`: pre-execution failure with schema reference, generated arguments, validation errors, and `argument_invalid`.
- `mcp_tool_execution_failed_trace.json`: execution-stage failure such as runtime error or timeout after valid selection and arguments.
- `mcp_result_misinterpreted_trace.json`: post-execution failure where the tool result exists but the Agent's result consumption contradicts or ignores important fields.

Future candidate fixtures:

```text
connection_failed
discovery_failed
tool_not_found
tool_selection_wrong
permission_denied
tool_result_invalid
insufficient_recovery_evidence
```

## 14. Acceptance Criteria

The Phase 2 implementation is complete only when:

- MCP adapter layer exists under `src/lumiagent/adapters/mcp/`.
- Core tracing models remain unchanged unless explicitly justified.
- `McpFailureType` is defined outside Core.
- MCP span `metadata.type` and artifact `metadata.type` constants are centralized.
- Helper functions create standard MCP spans, artifacts, inputs, outputs, and metadata.
- Successful MCP fixture validates as an `AgentRun`.
- `argument_invalid` fixture includes `schema_artifact_id`, generated arguments, `validation_errors`, `call_span_id`, and `failure_type`.
- `tool_execution_failed` fixture includes valid arguments, execution error details, `latency_ms`, `call_span_id`, and `failure_type`.
- `result_misinterpreted` fixture includes `result_artifact_id`, `consumed_artifact_ids`, `claimed_facts`, `contradicted_fields`, `ignored_key_fields`, and `failure_type`.
- Tests cover helper output shape, fixture serialization, and validator compatibility.
- `docs/PROJECT_SPEC.md` and `docs/PROJECT_SPEC.zh-CN.md` link to this formal spec.

Recommended verification commands:

```powershell
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

## 15. Design Summary

Phase 2 should make MCP tool-chain behavior observable as structured trace evidence. It should preserve the existing Trace Core, establish MCP-specific conventions in an adapter layer, and prepare stable evidence for later Coding Agent workflow modeling and diagnosis.
