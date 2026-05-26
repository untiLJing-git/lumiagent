# MCP Tool Chain Model Design Discussion

This document records the design decisions from the Phase 2 MCP Tool Chain Model discussion. The authoritative project specification is:

```text
docs/specs/mcp-tool-chain-model.md
```

## Decision Summary

Phase 2 will use the **MCP Adapter Evidence Layer** approach.

It establishes MCP tool-chain evidence conventions under:

```text
src/lumiagent/adapters/mcp/
```

It does not modify the generic Trace Core and does not connect to a real MCP SDK or MCP Server in this phase.

## Product Direction

The discussion emphasized product value before technical fields. MCP Tool Chain observability should explain failures in how Coding Agents use tools, not merely record tool calls.

The main target scenario is:

```text
Coding Agent uses MCP tools
```

The model should remain compatible with general Agent MCP flows, but MCP server developer debugging is not the primary Phase 2 goal.

## Phase Boundary

Phase 2 is an evidence layer for MCP tool-chain behavior.

Phase 3 will consume this evidence inside a complete Coding Agent workflow.

Phase 4 will consume the evidence to generate evaluation and diagnosis outputs.

The group clarified that MCP may look like a subset of Coding Agent Trace from an application perspective, but it deserves a separate phase because tool discovery, schema, arguments, permission, execution, and result consumption form an independent high-risk layer.

## Core Design Choices

- Use `src/lumiagent/adapters/mcp/` because future MCP SDK integration is expected.
- Keep `src/lumiagent/tracing/` framework-agnostic and MCP-free.
- Use `SpanKind.CUSTOM + metadata.type` for MCP process spans.
- Use `SpanKind.TOOL + metadata.type = "mcp_tool_execution"` for actual tool execution.
- Store tool schema snapshots as artifacts, not metadata.
- Store generated tool arguments in `tool_execution.input`.
- Store tool results as artifacts.
- Store result consumption evidence with medium granularity.

## Failure Taxonomy Decision

The taxonomy should have medium coverage, not a tiny or exhaustive list. It should be stable enough for Phase 4 evaluators to consume.

Failure types live in the MCP adapter layer, not in Core.

## Fixture Decision

Required initial fixtures:

```text
mcp_success_trace.json
mcp_argument_invalid_trace.json
mcp_tool_execution_failed_trace.json
mcp_result_misinterpreted_trace.json
```

This covers:

```text
success path
pre-execution failure
execution failure
post-execution interpretation failure
```

Other failures such as `connection_failed`, `discovery_failed`, `tool_not_found`, `tool_selection_wrong`, `permission_denied`, `tool_result_invalid`, and `insufficient_recovery_evidence` are future candidate fixtures.

## Documentation Structure Decision

The formal long-term spec lives in:

```text
docs/specs/mcp-tool-chain-model.md
```

This discussion record remains in:

```text
docs/superpowers/specs/2026-05-26-mcp-tool-chain-model-design.md
```

The formal spec is the source of truth. This file records why the decisions were made.
