"""Map MCP runtime results into LumiAgent trace runs."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lumiagent.adapters.mcp.builder import (
    add_mcp_failure_evidence,
    add_mcp_initialization,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    add_mcp_tool_selection,
    start_mcp_tool_chain,
)
from lumiagent.tracing import RunStatus, SpanStatus, TargetType
from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.models import AgentRun, utc_now

if TYPE_CHECKING:
    from lumiagent.adapters.mcp.runtime import (
        McpConnectionInfo,
        McpRuntimeError,
        McpSessionInfo,
        McpToolCallResult,
        McpToolDefinition,
    )
    from lumiagent.adapters.mcp.selector import McpToolSelection


class McpTraceMapper:
    """Create trace runs from already-captured MCP runtime outputs."""

    def map_success(
        self,
        *,
        run_name: str,
        connection: McpConnectionInfo,
        session: McpSessionInfo,
        tools: list[McpToolDefinition],
        selection: McpToolSelection,
        result: McpToolCallResult,
    ) -> AgentRun:
        builder = TraceBuilder(
            name=run_name,
            input_value={
                "server_name": connection.server_name,
                "transport": connection.transport,
                "requested_tool_name": selection.requested_tool_name,
            },
        )
        chain_id = start_mcp_tool_chain(
            builder,
            server_name=connection.server_name,
            metadata=self._connection_metadata(connection),
        )
        self._add_session_evidence(builder, chain_id, connection, session)
        schema_artifact_id = self._add_schema_snapshot(builder, chain_id, connection, tools)
        self._add_selection_evidence(builder, chain_id, connection, selection)
        execution_id = add_mcp_tool_execution(
            builder,
            chain_id,
            server_name=connection.server_name,
            tool_name=selection.selected_tool_name,
            arguments=result.arguments,
            schema_artifact_id=schema_artifact_id,
            validation={"status": "not_validated_by_mapper", "errors": []},
        )
        add_mcp_tool_result(
            builder,
            execution_id,
            content=result.content,
            latency_ms=result.latency_ms,
            status="error" if result.is_error else "success",
        )
        execution_status = SpanStatus.ERROR if result.is_error else SpanStatus.SUCCESS
        builder.end_span(
            execution_id,
            status=execution_status,
            output={"status": "error" if result.is_error else "success"},
        )
        builder.end_span(chain_id, status=execution_status)
        return builder.build(
            status=RunStatus.ERROR if result.is_error else RunStatus.SUCCESS,
            output={"tool_name": result.tool_name, "is_error": result.is_error},
        )

    def map_failure(
        self,
        *,
        run_name: str,
        connection: McpConnectionInfo,
        session: McpSessionInfo | None,
        tools: list[McpToolDefinition],
        requested_tool_name: str,
        error: McpRuntimeError,
    ) -> AgentRun:
        builder = TraceBuilder(
            name=run_name,
            input_value={
                "server_name": connection.server_name,
                "transport": connection.transport,
                "requested_tool_name": requested_tool_name,
            },
        )
        chain_id = start_mcp_tool_chain(
            builder,
            server_name=connection.server_name,
            metadata=self._connection_metadata(connection),
        )
        if session is not None:
            self._add_session_evidence(builder, chain_id, connection, session)
        schema_artifact_id = self._add_schema_snapshot(builder, chain_id, connection, tools)
        evidence_span_id = self._add_failure_span(
            builder,
            chain_id,
            connection,
            requested_tool_name,
            tools,
            schema_artifact_id,
            error,
        )
        builder.end_span(chain_id, status=SpanStatus.ERROR)
        builder.add_diagnosis(
            target_type=TargetType.RUN,
            target_id=builder.run.run_id,
            failure_type=error.failure_type.value,
            summary=error.message,
            evidence_span_ids=[evidence_span_id],
            suggested_fix=(
                "Inspect MCP runtime failure evidence and retry with a valid tool request."
            ),
        )
        return builder.build(
            status=RunStatus.ERROR,
            output={"status": "error", "failure_type": error.failure_type.value},
        )

    def _add_session_evidence(
        self,
        builder: TraceBuilder,
        chain_id: str,
        connection: McpConnectionInfo,
        session: McpSessionInfo,
    ) -> str:
        return add_mcp_initialization(
            builder,
            chain_id,
            server_name=session.server_name or connection.server_name,
            protocol_version=session.protocol_version,
            capabilities=session.capabilities,
        )

    def _add_schema_snapshot(
        self,
        builder: TraceBuilder,
        chain_id: str,
        connection: McpConnectionInfo,
        tools: list[McpToolDefinition],
    ) -> str:
        return add_mcp_tool_schema_snapshot(
            builder,
            chain_id,
            server_name=connection.server_name,
            captured_at=utc_now().isoformat(),
            tools=[self._tool_definition_to_snapshot(tool) for tool in tools],
        )

    def _add_selection_evidence(
        self,
        builder: TraceBuilder,
        chain_id: str,
        connection: McpConnectionInfo,
        selection: McpToolSelection,
    ) -> str:
        return add_mcp_tool_selection(
            builder,
            chain_id,
            server_name=connection.server_name,
            requested_tool_name=selection.requested_tool_name,
            selected_tool_name=selection.selected_tool_name,
            available_tool_names=selection.available_tool_names,
            selection_strategy=selection.selection_strategy,
            reason=selection.reason,
        )

    def _add_failure_span(
        self,
        builder: TraceBuilder,
        chain_id: str,
        connection: McpConnectionInfo,
        requested_tool_name: str,
        tools: list[McpToolDefinition],
        schema_artifact_id: str,
        error: McpRuntimeError,
    ) -> str:
        selection_id = add_mcp_tool_selection(
            builder,
            chain_id,
            server_name=connection.server_name,
            requested_tool_name=requested_tool_name,
            selected_tool_name=None,
            available_tool_names=[tool.name for tool in tools],
            selection_strategy="explicit",
            reason=error.message,
        )
        add_mcp_failure_evidence(
            builder,
            selection_id,
            failure_type=error.failure_type,
            failure_stage=error.stage.value,
            server_name=connection.server_name,
            tool_name=requested_tool_name,
            schema_artifact_id=schema_artifact_id,
            evidence_span_ids=[selection_id],
            error_code=error.failure_type.value,
            error_message=error.message,
            raw_error_code=error.raw_error_code,
            raw_error_message=error.message,
            raw_error_data=self._raw_error_data(error.raw_error_data),
            runtime_stage=error.stage.value,
        )
        builder.end_span(selection_id, status=SpanStatus.ERROR, output={"status": "error"})
        return selection_id

    def _connection_metadata(self, connection: McpConnectionInfo) -> dict[str, Any]:
        return {
            "transport": connection.transport,
            "server_command": connection.server_command,
            "server_args": connection.server_args,
        }

    def _tool_definition_to_snapshot(self, tool: McpToolDefinition) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }

    def _raw_error_data(self, raw_error_data: Any) -> dict[str, Any] | None:
        if raw_error_data is None:
            return None
        if isinstance(raw_error_data, dict):
            return raw_error_data
        return {"value": raw_error_data}
