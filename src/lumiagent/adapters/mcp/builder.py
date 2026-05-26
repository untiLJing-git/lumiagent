"""Builder helpers for MCP trace spans, artifacts, and events."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
)
from lumiagent.adapters.mcp.schemas import (
    McpFailureEvidence,
    McpResultConsumptionEvidence,
    McpToolCallInput,
    McpToolExecutionSummary,
    McpToolSchemaSnapshot,
)
from lumiagent.tracing import ArtifactKind, EventLevel, SpanKind, SpanStatus

if TYPE_CHECKING:
    from lumiagent.adapters.mcp.taxonomy import McpFailureType
    from lumiagent.tracing.builder import TraceBuilder


def _merge_metadata(
    base: dict[str, Any], metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {**(metadata or {}), **base}


def start_mcp_tool_chain(
    builder: TraceBuilder,
    *,
    server_name: str,
    parent_span_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Start the root span for a logical MCP tool chain."""

    return builder.start_span(
        "MCP Tool Chain",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        metadata=_merge_metadata(
            {"type": MCP_SPAN_TOOL_CHAIN, "server_name": server_name}, metadata
        ),
    )


def add_mcp_tool_schema_snapshot(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    server_name: str,
    captured_at: str,
    tools: list[dict[str, Any]],
    schema_version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Record discovered MCP tool schemas under a short discovery span."""

    snapshot = McpToolSchemaSnapshot(
        server_name=server_name,
        captured_at=captured_at,
        schema_version=schema_version,
        tools=tools,
    )
    discovery_id = builder.start_span(
        "MCP Tool Discovery",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        metadata={"type": MCP_SPAN_DISCOVERY, "server_name": server_name},
    )
    artifact_id = builder.add_artifact(
        discovery_id,
        name="MCP Tool Schema Snapshot",
        kind=ArtifactKind.CUSTOM,
        content=snapshot.model_dump(mode="json"),
        metadata=_merge_metadata(
            {"type": MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT, "server_name": server_name},
            metadata,
        ),
    )
    builder.end_span(
        discovery_id,
        status=SpanStatus.SUCCESS,
        output={"tool_count": len(tools)},
    )
    return artifact_id


def add_mcp_tool_execution(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    schema_artifact_id: str | None = None,
    validation: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Start an MCP tool execution span with validated call input."""

    call_input = McpToolCallInput(
        server_name=server_name,
        tool_name=tool_name,
        schema_artifact_id=schema_artifact_id,
        arguments=arguments or {},
        validation=validation or {},
    )
    return builder.start_span(
        f"MCP Tool Execution: {tool_name}",
        kind=SpanKind.TOOL,
        parent_span_id=parent_span_id,
        input_value=call_input.model_dump(mode="json"),
        metadata=_merge_metadata(
            {
                "type": MCP_SPAN_TOOL_EXECUTION,
                "server_name": server_name,
                "tool_name": tool_name,
            },
            metadata,
        ),
    )


def add_mcp_tool_result(
    builder: TraceBuilder,
    execution_span_id: str,
    *,
    content: Any,
    latency_ms: int | None = None,
    status: Literal["success", "error"] = "success",
    failure_type: McpFailureType | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Attach an MCP tool result artifact and summary event to an execution span."""

    artifact_id = builder.add_artifact(
        execution_span_id,
        name="MCP Tool Result",
        kind=ArtifactKind.TOOL_RESULT,
        content=content,
        metadata=_merge_metadata({"type": MCP_ARTIFACT_TOOL_RESULT}, metadata),
    )
    summary = McpToolExecutionSummary(
        status=status,
        latency_ms=latency_ms,
        result_artifact_id=artifact_id,
        failure_type=failure_type,
    )
    builder.add_event(
        execution_span_id,
        name="mcp_tool_result_recorded",
        level=EventLevel.INFO,
        metadata=summary.model_dump(mode="json"),
    )
    return artifact_id


def add_mcp_failure_evidence(
    builder: TraceBuilder,
    span_id: str,
    *,
    failure_type: McpFailureType,
    failure_stage: str,
    server_name: str | None = None,
    tool_name: str | None = None,
    schema_artifact_id: str | None = None,
    call_span_id: str | None = None,
    result_artifact_id: str | None = None,
    evidence_span_ids: list[str] | None = None,
    expected: Any = None,
    actual: Any = None,
    validation_errors: list[dict[str, Any]] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
    permission_status: str | None = None,
    consumed_artifact_ids: list[str] | None = None,
    contradicted_fields: list[str] | None = None,
    ignored_key_fields: list[str] | None = None,
    notes: str = "",
) -> str:
    """Add a structured MCP failure evidence event."""

    evidence = McpFailureEvidence(
        failure_type=failure_type,
        failure_stage=failure_stage,
        server_name=server_name,
        tool_name=tool_name,
        schema_artifact_id=schema_artifact_id,
        call_span_id=call_span_id,
        result_artifact_id=result_artifact_id,
        evidence_span_ids=evidence_span_ids or [],
        expected=expected,
        actual=actual,
        validation_errors=validation_errors or [],
        error_code=error_code,
        error_message=error_message,
        latency_ms=latency_ms,
        permission_status=permission_status,
        consumed_artifact_ids=consumed_artifact_ids or [],
        contradicted_fields=contradicted_fields or [],
        ignored_key_fields=ignored_key_fields or [],
        notes=notes,
    )
    return builder.add_event(
        span_id,
        name="mcp_failure_evidence",
        level=EventLevel.ERROR,
        metadata=evidence.model_dump(mode="json"),
    )


def add_mcp_result_consumption(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    consumed_artifact_ids: list[str],
    consumption_summary: str,
    claimed_facts: list[str] | None = None,
    contradicted_fields: list[str] | None = None,
    ignored_key_fields: list[str] | None = None,
    confidence: float | None = None,
    notes: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Start a span capturing how the agent consumed MCP tool results."""

    evidence = McpResultConsumptionEvidence(
        consumed_artifact_ids=consumed_artifact_ids,
        consumption_summary=consumption_summary,
        claimed_facts=claimed_facts or [],
        contradicted_fields=contradicted_fields or [],
        ignored_key_fields=ignored_key_fields or [],
        confidence=confidence,
        notes=notes,
    )
    return builder.start_span(
        "MCP Result Consumption",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        input_value=evidence.model_dump(mode="json"),
        metadata=_merge_metadata({"type": MCP_SPAN_RESULT_CONSUMPTION}, metadata),
    )
