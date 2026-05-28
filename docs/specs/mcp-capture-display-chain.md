# MCP Capture + Display Chain Specification

## 1. Purpose

Phase 2b establishes LumiAgent's first real MCP capture and display chain. Its purpose is to close the minimal capture-model-display loop for third-party MCP Server interactions while preserving the adapter boundary established in Phase 2a.

This phase is not a fake demo-server path. LumiAgent must be able to connect to a real third-party MCP Server, discover tools, record schema and selection evidence, call a selected tool, capture result or failure evidence, convert the interaction into a valid `AgentRun`, and render the trace through a minimal CLI viewer.

The first implementation supports stdio transport. The architecture must remain transport-agnostic so HTTP and SSE transports can be added later without rewriting capture strategy or trace mapping logic.

## 2. Product Value

Coding Agents increasingly depend on MCP tools for file access, search, execution, retrieval, and external system operations. When an MCP tool-chain fails, a final benchmark score rarely explains whether the failure came from server connection, tool discovery, tool selection, argument generation, permission boundaries, tool execution, timeout, transport interruption, invalid result shape, or result consumption.

MCP Capture + Display gives LumiAgent a concrete way to answer:

- Which real MCP server was connected?
- Which transport and launch configuration were used?
- Did MCP initialization succeed?
- Which tools and schemas were available?
- Which tool was requested, and was it actually available?
- Which arguments were sent to the tool?
- Did the tool return a result, an MCP error, a permission failure, or a timeout?
- Which span and artifact provide evidence for the failure type?
- Can a human inspect the trace in a terminal without writing custom code?

The value is not only MCP invocation. The value is a durable evidence chain that later Coding Agent Trace, Evaluation / Diagnosis, Replay, and Visualization phases can consume.

## 3. Scope

Phase 2b includes:

```text
CaptureStrategy protocol
McpCaptureStrategy
McpClientRuntime protocol
StdioMcpClientRuntime
ExplicitToolSelector
McpTraceMapper
lumiagent capture mcp
lumiagent show
expanded McpFailureType taxonomy
third-party filesystem MCP verification path
```

The phase must use the existing Trace Core and Phase 2a MCP evidence layer:

```text
AgentRun
Span
Artifact
Evaluation / Diagnosis evidence references
MCP metadata.type conventions
MCP evidence schemas
MCP builder helpers
```

The generated trace must validate through Trace Core validation and must keep MCP-specific semantics in `src/lumiagent/adapters/mcp/` or capture/viewer layers rather than adding MCP-specific fields to Trace Core.

## 4. Non-goals

Phase 2b does not include:

- A fake or built-in MCP demo server as the primary path.
- HTTP, SSE, or WebSocket transport implementation.
- Multi-tool workflow orchestration.
- Automatic LLM-based tool selection.
- Claude Code hooks capture.
- MCP proxy implementation.
- Claude Desktop config import.
- Web UI, TUI, dashboard, or timeline visualization.
- Automatic semantic result-misinterpretation diagnosis.
- Persistent trace storage beyond writing JSON files.
- MCP-specific fields on Trace Core models.

## 5. Architecture Boundary

Recommended module layout:

```text
src/lumiagent/capture/
  __init__.py
  strategy.py

src/lumiagent/adapters/mcp/
  capture.py
  runtime.py
  selector.py
  mapper.py
  viewer.py
  taxonomy.py
  schemas.py
  conventions.py
  builder.py
```

Responsibilities:

- `capture/strategy.py`: generic `CaptureStrategy` protocol.
- `adapters/mcp/runtime.py`: transport-agnostic runtime protocol and stdio implementation.
- `adapters/mcp/selector.py`: explicit tool selection and selection evidence payloads.
- `adapters/mcp/mapper.py`: conversion from MCP runtime outputs to Trace Core spans/artifacts.
- `adapters/mcp/capture.py`: `McpCaptureStrategy` orchestration.
- `adapters/mcp/viewer.py`: MCP evidence extraction for CLI display.
- Existing Phase 2a files continue to own conventions, schemas, taxonomy, and builder helpers.

The generic `src/lumiagent/tracing/` package remains framework-agnostic and must not import MCP adapter modules.

## 6. Capture Strategy

`CaptureStrategy` is the unified capture entry point for all current and future capture methods.

Required shape:

```text
capture() -> AgentRun
```

Phase 2b provides the first implementation:

```text
McpCaptureStrategy
```

Future implementations should fit the same concept:

```text
ClaudeCodeHooksStrategy
TranscriptImportStrategy
SdkDecoratorStrategy
McpProxyStrategy
```

## 7. MCP Client Runtime

`McpClientRuntime` is a transport-agnostic runtime protocol. It describes the MCP communication operations that capture needs without exposing whether the server is reached through stdio, HTTP, SSE, or another transport.

Required operations:

```text
connect() -> McpConnectionInfo
initialize() -> McpSessionInfo
list_tools() -> list[McpToolDefinition]
call_tool(name, arguments) -> McpToolCallResult
close() -> None
```

Phase 2b implements:

```text
StdioMcpClientRuntime
```

Future transports should implement the same protocol:

```text
HttpMcpClientRuntime
SseMcpClientRuntime
```

The runtime layer owns process/session communication details. It does not select tools, classify product-level failures, print CLI output, or construct Trace Core objects.

## 8. Tool Selection Evidence

MCP tool usage includes a selection step between discovery and execution:

```text
tool discovery -> tool selection -> tool call
```

Phase 2b supports explicit tool selection only. The user chooses the tool through CLI:

```text
--tool read_file
```

`ExplicitToolSelector` checks the requested tool against discovered tools.

Successful selection records:

```text
requested_tool_name
selected_tool_name
available_tool_names
selection_strategy = explicit
reason
```

Missing tool selection records a `tool_not_found` failure and should produce a trace where the failure is attributable to tool selection, not tool execution.

Phase 2b does not implement automatic tool planning. Future selectors may include:

```text
RuleBasedToolSelector
LlmToolSelector
ReplayToolSelector
```

They should preserve the same selection evidence shape.

## 9. Recommended Capture Flow

A successful stdio MCP capture follows this flow:

```text
CLI arguments
  -> McpCaptureConfig
  -> McpCaptureStrategy
  -> StdioMcpClientRuntime.connect
  -> StdioMcpClientRuntime.initialize
  -> StdioMcpClientRuntime.list_tools
  -> ExplicitToolSelector.select
  -> StdioMcpClientRuntime.call_tool
  -> McpTraceMapper
  -> AgentRun(status=success)
  -> trace JSON
```

A failed MCP capture follows the same flow as far as possible, but maps the failing stage into a valid error trace:

```text
MCP runtime / selection failure
  -> McpFailureType
  -> failure evidence artifact
  -> AgentRun(status=error)
  -> trace JSON
```

## 10. Recommended Span Tree

Successful MCP capture should produce a span tree similar to:

```text
mcp_tool_chain span [success]
├── mcp_connection span [success]
├── mcp_initialization span [success]
├── mcp_discovery span [success]
│   └── mcp_tool_schema_snapshot artifact
├── mcp_tool_selection span [success]
│   └── mcp_tool_selection artifact
└── mcp_tool_execution span [success]
    ├── input: tool arguments and schema reference
    ├── artifact: mcp_tool_result
    └── output: execution summary
```

Failed capture should mark the failing span and parent chain appropriately:

```text
mcp_tool_chain span [error]
├── mcp_connection span [success]
├── mcp_initialization span [success]
├── mcp_discovery span [success]
├── mcp_tool_selection span [error]
│   └── mcp_failure_evidence artifact
└── optional later spans omitted
```

Actual tool execution uses `SpanKind.TOOL`. Aggregation and process spans use generic/custom spans with MCP `metadata.type` conventions.

## 11. Failure Taxonomy

Phase 2b expands `McpFailureType` so real third-party MCP capture can classify failures beyond sample fixtures.

Required stable values:

```text
connection_failed
initialization_failed
tool_discovery_failed
tool_not_found
argument_invalid
permission_denied
tool_execution_failed
timeout
transport_interrupted
result_invalid
result_misinterpreted
unknown
```

Existing values must remain stable:

```text
argument_invalid
tool_execution_failed
result_misinterpreted
```

`McpFailureType` is a LumiAgent diagnosis taxonomy. It is not a complete mirror of MCP protocol error codes or third-party server-specific errors.

Raw error evidence should be preserved separately:

```text
raw_error_code
raw_error_message
raw_error_data
transport
server_command
tool_name
arguments
runtime_stage
```

`result_misinterpreted` remains in the taxonomy for Phase 3/4, but Phase 2b does not automatically infer result misinterpretation because that requires observing how an Agent consumes a successful result.

## 12. CLI Requirements

### 12.1 Capture Command

Required command shape:

```powershell
lumiagent capture mcp `
  --transport stdio `
  --server-command "npx" `
  --server-arg "-y" `
  --server-arg "@modelcontextprotocol/server-filesystem" `
  --server-arg "$PWD" `
  --tool "read_file" `
  --arguments '{"path":"README.md"}' `
  -o ".lumiagent/traces/filesystem-read-success.json"
```

Required parameters:

```text
--transport stdio
--server-command <command>
--server-arg <arg>          repeatable
--tool <tool-name>
--arguments <json-object>
-o / --output <trace-path>
```

Optional parameter:

```text
--timeout-seconds <seconds>
```

`--transport` is required even though only stdio is supported in Phase 2b. This keeps the CLI explicit and reserves the shape for HTTP/SSE.

### 12.2 Show Command

Required command shape:

```powershell
lumiagent show ".lumiagent/traces/filesystem-read-success.json"
```

The initial viewer must print:

- Run name, status, and duration when available.
- Span tree.
- MCP transport and server command summary.
- Tool discovery summary.
- Tool selection summary.
- Tool schema summary.
- Tool arguments.
- Result summary or failure summary.
- Evidence span IDs.

Example success output:

```text
Run: filesystem read success
Status: success

Span Tree:
- MCP Tool Chain [success]
  - Connect server [success]
  - Initialize session [success]
  - Discover tools [success]
  - Select tool: read_file [success]
  - Call tool: read_file [success]

Tool Selection:
  strategy: explicit
  requested: read_file
  selected: read_file

Tool Call:
  arguments:
    path: README.md
```

Example failure output:

```text
Run: filesystem tool not found
Status: error

Span Tree:
- MCP Tool Chain [error]
  - Connect server [success]
  - Initialize session [success]
  - Discover tools [success]
  - Select tool: read_me [error]

MCP Failure:
  type: tool_not_found
  requested tool: read_me
  available tools: read_file, list_directory, search_files
  evidence spans: span_xxx
```

## 13. Error Handling

### 13.1 CLI Argument Errors

These errors fail immediately and do not create trace files:

- Invalid `--arguments` JSON.
- `--arguments` is not a JSON object.
- Missing `--server-command`.
- Missing `--tool`.
- Unsupported `--transport`.
- Output path cannot be written.

### 13.2 MCP Runtime Errors

Once capture has started, these errors should create `AgentRun(status=error)` whenever enough context exists:

- Connection failure.
- Initialization failure.
- Tool discovery failure.
- Tool not found.
- Tool call error.
- Timeout.
- Transport interruption.
- Invalid result shape.

The CLI may return a non-zero exit code while still writing a trace file when a valid error trace can be constructed.

## 14. Third-Party Verification Path

The required real third-party verification path uses a filesystem MCP server because it is local, Coding Agent relevant, and does not require authentication.

Success path:

```powershell
lumiagent capture mcp `
  --transport stdio `
  --server-command "npx" `
  --server-arg "-y" `
  --server-arg "@modelcontextprotocol/server-filesystem" `
  --server-arg "$PWD" `
  --tool "read_file" `
  --arguments '{"path":"README.md"}' `
  -o ".lumiagent/traces/filesystem-read-success.json"

lumiagent show ".lumiagent/traces/filesystem-read-success.json"
```

Failure path:

```powershell
lumiagent capture mcp `
  --transport stdio `
  --server-command "npx" `
  --server-arg "-y" `
  --server-arg "@modelcontextprotocol/server-filesystem" `
  --server-arg "$PWD" `
  --tool "read_me" `
  --arguments '{"path":"README.md"}' `
  -o ".lumiagent/traces/filesystem-tool-not-found.json"

lumiagent show ".lumiagent/traces/filesystem-tool-not-found.json"
```

The failure path intentionally uses an invalid tool name so the failure is stable and clearly attributable to tool selection.

## 15. Fixtures and Tests

Unit tests must not depend on a real third-party MCP server.

Required unit coverage:

- `CaptureStrategy` protocol importability.
- `McpCaptureConfig` validation.
- Runtime result and error models.
- `ExplicitToolSelector` success and `tool_not_found` failure.
- `McpTraceMapper` success mapping to valid `AgentRun`.
- `McpTraceMapper` failure mapping to valid `AgentRun(status=error)`.
- Expanded `McpFailureType` stable values.
- CLI parser validation for JSON arguments, repeated `--server-arg`, and transport.
- Viewer output includes span tree, tool selection, arguments, result or failure, and evidence IDs.

Executable verification must include the filesystem MCP success and failure commands in Section 14. Because those commands depend on Node/npm and third-party package availability, they may be manual or integration-level checks rather than default CI tests. The technical report must record whether they were run and what happened.

## 16. Acceptance Criteria

Phase 2b is complete when:

- `CaptureStrategy` exists as the unified capture entry point.
- `McpClientRuntime` exists as a transport-agnostic runtime protocol.
- `StdioMcpClientRuntime` can call a real third-party MCP server.
- `ExplicitToolSelector` records successful and failed tool selection evidence.
- `McpCaptureStrategy` produces valid `AgentRun` traces for success and failure.
- `McpFailureType` covers real connection, initialization, discovery, selection, execution, timeout, transport, and result-shape failures.
- `lumiagent capture mcp` writes trace JSON.
- `lumiagent show` renders MCP span tree and evidence summary.
- The filesystem MCP success and failure paths are locally executable.
- Unit tests cover capture config, runtime schemas, selector, mapper, taxonomy, CLI parsing, and viewer output.
- Required verification commands pass.
- A Chinese technical report records technology choices, design patterns, implementation details, validation results, risks, trade-offs, and follow-up suggestions.

## 17. Relationship to Later Phases

Phase 2b is the bridge from static MCP evidence modeling to real trace capture:

```text
Phase 2a MCP Tool Chain Model:
  defines MCP evidence schemas and builder conventions

Phase 2b MCP Capture + Display Chain:
  captures real third-party MCP interactions and displays their evidence

Phase 3 Coding Agent Trace Model:
  embeds MCP capture evidence inside full coding workflows and Claude Code hooks traces

Phase 4 Evaluation / Diagnosis Engine:
  consumes MCP failure evidence to diagnose tool misuse, argument errors, permission failures, and insufficient recovery

Phase 5 Replay / Visualization Preparation:
  projects captured MCP traces into timeline, span tree, detail, diagnosis, and diff view models
```

Transport expansion should happen by adding new `McpClientRuntime` implementations. Capture semantics, trace mapping, and CLI display should remain stable across transports.
