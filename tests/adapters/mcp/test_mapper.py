from lumiagent.adapters.mcp import (
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_INITIALIZATION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
    McpFailureType,
)
from lumiagent.adapters.mcp.mapper import McpTraceMapper
from lumiagent.adapters.mcp.runtime import (
    McpConnectionInfo,
    McpRuntimeError,
    McpRuntimeStage,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
)
from lumiagent.adapters.mcp.selector import McpToolSelection
from lumiagent.tracing import RunStatus, SpanStatus, TargetType
from lumiagent.tracing.validator import validate_run


def test_success_mapper_creates_valid_agent_run_with_mcp_evidence() -> None:
    connection = McpConnectionInfo(
        transport="stdio",
        server_name="filesystem",
        server_command="mcp-filesystem",
        server_args=["."],
    )
    session = McpSessionInfo(
        protocol_version="2024-11-05",
        server_name="filesystem",
        capabilities={"tools": True},
    )
    tools = [
        McpToolDefinition(
            name="read_file",
            description="Read a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )
    ]
    selection = McpToolSelection(
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file"],
        selection_strategy="explicit",
        reason="Tool name was provided by CLI.",
    )
    result = McpToolCallResult(
        tool_name="read_file",
        arguments={"path": "README.md"},
        content=[{"type": "text", "text": "# LumiAgent"}],
        latency_ms=12,
    )

    run = McpTraceMapper().map_success(
        run_name="Read README",
        connection=connection,
        session=session,
        tools=tools,
        selection=selection,
        result=result,
    )

    validate_run(run)
    assert run.name == "Read README"
    assert run.status is RunStatus.SUCCESS
    assert len(run.root_spans) == 1

    chain = run.root_spans[0]
    assert chain.status is SpanStatus.SUCCESS
    assert chain.metadata["type"] == MCP_SPAN_TOOL_CHAIN
    assert chain.metadata["server_name"] == "filesystem"
    assert chain.metadata["transport"] == "stdio"

    child_types = [child.metadata["type"] for child in chain.children]
    assert child_types == [
        MCP_SPAN_INITIALIZATION,
        MCP_SPAN_DISCOVERY,
        MCP_SPAN_TOOL_SELECTION,
        MCP_SPAN_TOOL_EXECUTION,
    ]

    init_span, discovery_span, selection_span, execution_span = chain.children
    assert init_span.input["protocol_version"] == "2024-11-05"
    assert discovery_span.artifacts[0].content["tools"][0]["name"] == "read_file"
    assert selection_span.artifacts[0].content["selected_tool_name"] == "read_file"
    assert execution_span.status is SpanStatus.SUCCESS
    assert execution_span.input["arguments"] == {"path": "README.md"}
    assert execution_span.artifacts[0].content == [{"type": "text", "text": "# LumiAgent"}]
    assert run.output == {"tool_name": "read_file", "is_error": False}


def test_failure_mapper_creates_valid_error_run_with_diagnosis_and_evidence() -> None:
    connection = McpConnectionInfo(transport="stdio", server_name="filesystem")
    session = McpSessionInfo(protocol_version="2024-11-05", capabilities={"tools": True})
    tools = [McpToolDefinition(name="write_file", input_schema={"type": "object"})]
    error = McpRuntimeError(
        failure_type=McpFailureType.TOOL_NOT_FOUND,
        stage=McpRuntimeStage.TOOL_SELECTION,
        message="Tool 'read_file' was not found.",
        raw_error_code="tool_not_found",
        raw_error_data={"available_tools": ["write_file"]},
    )

    run = McpTraceMapper().map_failure(
        run_name="Read README",
        connection=connection,
        session=session,
        tools=tools,
        requested_tool_name="read_file",
        error=error,
    )

    validate_run(run)
    assert run.status is RunStatus.ERROR
    assert len(run.diagnoses) == 1
    diagnosis = run.diagnoses[0]
    assert diagnosis.target_type is TargetType.RUN
    assert diagnosis.target_id == run.run_id
    assert diagnosis.failure_type == "tool_not_found"
    assert diagnosis.evidence_span_ids

    chain = run.root_spans[0]
    assert chain.status is SpanStatus.ERROR
    child_types = [child.metadata["type"] for child in chain.children]
    assert child_types == [MCP_SPAN_INITIALIZATION, MCP_SPAN_DISCOVERY, MCP_SPAN_TOOL_SELECTION]

    selection_span = chain.children[-1]
    assert selection_span.status is SpanStatus.ERROR
    assert selection_span.span_id in diagnosis.evidence_span_ids
    assert selection_span.artifacts[0].content["requested_tool_name"] == "read_file"
    assert selection_span.artifacts[0].content["selected_tool_name"] is None
    evidence_event = selection_span.events[0]
    assert evidence_event.name == "mcp_failure_evidence"
    assert evidence_event.metadata["failure_type"] == "tool_not_found"
    assert evidence_event.metadata["runtime_stage"] == "tool_selection"
    assert evidence_event.metadata["raw_error_data"] == {"available_tools": ["write_file"]}
    assert run.output == {"status": "error", "failure_type": "tool_not_found"}
