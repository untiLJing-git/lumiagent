# Third-Party MCP Capture Path Design

## Purpose

Phase 2b establishes LumiAgent's first real third-party MCP Server capture and analysis path. It is not a fake demo server path. It must prove that LumiAgent can connect to an external MCP server, capture tool-chain evidence, convert the interaction into a valid `AgentRun`, and render the result through a minimal CLI viewer.

The first supported transport is stdio, but the architecture must remain transport-agnostic so HTTP and SSE can be added later without rewriting capture mapping logic.

## Goals

- Capture a real third-party MCP Server interaction through the CLI.
- Record connection, initialization, tool discovery, tool selection, schema snapshot, tool call arguments, result, and error evidence.
- Convert successful and failed MCP interactions into valid Trace Core `AgentRun` objects.
- Display MCP span tree and evidence through `lumiagent show <trace.json>`.
- Establish `CaptureStrategy` as the shared entry point for future capture methods.
- Keep MCP-specific semantics in the adapter layer, not Trace Core.

## Non-Goals

- No fake or built-in MCP demo server as the primary path.
- No HTTP, SSE, or WebSocket transport implementation in the first version.
- No multi-tool workflow orchestration.
- No automatic LLM-based tool selection.
- No Claude Code hooks capture.
- No MCP proxy.
- No Claude Desktop config import.
- No Web UI or TUI.
- No automatic semantic result-misinterpretation diagnosis.

## Architecture

```text
CaptureStrategy
└── McpCaptureStrategy
    ├── McpClientRuntime
    │   └── StdioMcpClientRuntime
    ├── ExplicitToolSelector
    ├── McpTraceMapper
    └── AgentRun
```

### CaptureStrategy

`CaptureStrategy` is the unified capture entry point:

```text
capture() -> AgentRun
```

Future capture implementations such as Claude Code hooks, transcript import, SDK decorators, and MCP proxy capture should use the same shape.

### McpCaptureStrategy

`McpCaptureStrategy` coordinates one MCP capture run:

1. Create the root MCP tool-chain trace context.
2. Connect to the configured MCP runtime.
3. Initialize the MCP session.
4. Discover available tools.
5. Select the requested tool through `ExplicitToolSelector`.
6. Call the selected tool with user-provided arguments.
7. Map success or failure into MCP evidence artifacts and spans.
8. Return a valid `AgentRun`.

It depends on `McpClientRuntime`, `ToolSelector`, and `McpTraceMapper` interfaces rather than concrete stdio implementation details.

### McpClientRuntime

`McpClientRuntime` is a transport-agnostic runtime protocol. It describes MCP communication capabilities without binding the capture layer to stdio, HTTP, or SSE.

Required operations:

```text
connect() -> McpConnectionInfo
initialize() -> McpSessionInfo
list_tools() -> list[McpToolDefinition]
call_tool(name, arguments) -> McpToolCallResult
close() -> None
```

The first implementation is:

```text
StdioMcpClientRuntime
```

Future implementations can be added behind the same protocol:

```text
HttpMcpClientRuntime
SseMcpClientRuntime
```

### ExplicitToolSelector

Phase 2b supports explicit tool selection only. The user selects the tool at capture time through `--tool`.

`ExplicitToolSelector` receives:

```text
requested_tool_name
available tool definitions
```

It returns a `McpToolSelection` when the tool exists, or a `tool_not_found` failure when it does not.

This models the tool-selection step without introducing automatic tool planning. Future selectors can include rule-based, LLM-based, or replay-based selectors while preserving the same evidence shape.

Selection evidence should record:

```text
requested_tool_name
selected_tool_name
available_tool_names
selection_strategy = explicit
reason
```

### McpTraceMapper

`McpTraceMapper` maps runtime and selection outputs into Phase 2a MCP evidence conventions:

- MCP tool-chain span.
- Connection span.
- Initialization span.
- Tool discovery span.
- Tool selection span.
- Tool call span.
- Schema snapshot artifact.
- Tool selection artifact.
- Tool call arguments artifact.
- Execution summary artifact.
- Tool result artifact.
- Failure evidence artifact.

It must reuse the MCP adapter layer and must not add MCP-specific fields to Trace Core models.

## CLI Design

### Capture Command

The first CLI shape:

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

Supported arguments:

```text
--transport stdio
--server-command <command>
--server-arg <arg>          repeatable
--tool <tool-name>
--arguments <json-object>
-o / --output <trace-path>
--timeout-seconds <seconds>
```

The `--transport` argument is required even though only `stdio` is supported in Phase 2b. This makes transport selection explicit and reserves the CLI shape for HTTP/SSE.

### Show Command

```powershell
lumiagent show ".lumiagent/traces/filesystem-read-success.json"
```

The initial viewer should render:

- Run name, status, and duration.
- Span tree.
- MCP server command and transport.
- Tool discovery summary.
- Tool selection evidence.
- Tool schema summary.
- Tool arguments.
- Result summary or failure evidence.
- Evidence span IDs.

Example success output shape:

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

Example failure output shape:

```text
Run: filesystem read failure
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

## Failure Taxonomy

Phase 2b expands the MCP adapter failure taxonomy to support real third-party MCP capture:

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

Existing values must remain unchanged:

```text
argument_invalid
tool_execution_failed
result_misinterpreted
```

`McpFailureType` is a LumiAgent diagnosis taxonomy, not a mirror of every MCP protocol error or every third-party server error code. Raw MCP errors should be preserved in failure evidence artifacts:

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

`result_misinterpreted` remains in the taxonomy, but Phase 2b does not automatically infer it because that requires observing how an agent consumes tool results.

## Error Handling

### CLI Argument Errors

These fail immediately and do not generate trace files:

- Invalid `--arguments` JSON.
- `--arguments` is not a JSON object.
- Missing `--server-command`.
- Missing `--tool`.
- Unsupported `--transport`.
- Output path cannot be written.

### MCP Runtime Errors

Once capture has started, runtime errors should generate `AgentRun(status=error)` whenever enough context exists:

- Connection failure.
- Initialization failure.
- Tool discovery failure.
- Tool not found.
- Tool call error.
- Timeout.
- Transport interruption.
- Invalid result shape.

The CLI may still return a non-zero exit code, but the trace file should exist when a trace could be constructed.

## Third-Party Verification Path

The primary verification path uses a real third-party filesystem MCP server because it is local, code-agent relevant, and requires no authentication.

Success case:

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

Failure case:

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

The failure case intentionally uses an invalid tool name so the failure is stable and clearly attributable to tool selection.

## Testing Strategy

Unit tests must not depend on real third-party MCP servers.

Required unit coverage:

- `CaptureStrategy` protocol importability.
- `McpCaptureConfig` validation.
- Runtime result and error models.
- `ExplicitToolSelector` success and `tool_not_found` failure.
- `McpTraceMapper` success mapping to valid `AgentRun`.
- `McpTraceMapper` failure mapping to valid `AgentRun(status=error)`.
- Expanded `McpFailureType` stable enum values.
- CLI parser validation for JSON arguments, repeated server args, and transport.
- Viewer output includes span tree, tool selection, arguments, result/failure, and evidence IDs.

Executable verification must include the filesystem MCP success and failure commands above. This can be manual or integration-level because it depends on Node/npm and third-party package availability, but the technical report must record whether it was run and what happened.

## Acceptance Criteria

Phase 2b is complete when:

1. `CaptureStrategy` exists as the unified capture entry point.
2. `McpClientRuntime` exists as a transport-agnostic runtime protocol.
3. `StdioMcpClientRuntime` can call a real third-party MCP server.
4. `ExplicitToolSelector` records successful and failed tool selection evidence.
5. `McpCaptureStrategy` produces valid `AgentRun` traces for success and failure.
6. `McpFailureType` covers real connection, initialization, discovery, selection, execution, timeout, transport, and result-shape failures.
7. `lumiagent capture mcp` writes trace JSON.
8. `lumiagent show` renders MCP span tree and evidence summary.
9. The filesystem MCP success and failure paths are locally executable.
10. `python -m pytest -v` passes.
11. `python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters` passes, expanded if new packages require it.
12. `python -m mypy src/lumiagent/tracing src/lumiagent/adapters` passes, expanded if new packages require it.
13. A Chinese technical report records technology choices, design patterns, implementation details, validation results, risks, trade-offs, and follow-up suggestions.

## Design Notes

The design uses Strategy Pattern for capture methods, Adapter Pattern for MCP transports, and Ports and Adapters architecture for isolating capture logic from transport details. The core product value remains MCP tool-chain evidence, not stdio-specific process management.

This design intentionally keeps automatic tool selection out of Phase 2b. Explicit selection still records the tool-selection stage so later phases can diagnose wrong-tool or missing-tool failures and eventually replace `ExplicitToolSelector` with richer selectors.
