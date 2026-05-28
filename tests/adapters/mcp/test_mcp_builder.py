from lumiagent.adapters.mcp import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_ARTIFACT_TOOL_SELECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_INITIALIZATION,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
    McpFailureType,
)
from lumiagent.adapters.mcp.builder import (
    add_mcp_failure_evidence,
    add_mcp_initialization,
    add_mcp_result_consumption,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    add_mcp_tool_selection,
    start_mcp_tool_chain,
)
from lumiagent.tracing import ArtifactKind, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.validator import validate_run


def test_mcp_helpers_create_valid_success_trace() -> None:
    builder = TraceBuilder(run_id="run_mcp_success", name="MCP success")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    schema_id = add_mcp_tool_schema_snapshot(
        builder,
        chain_id,
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        tools=[{"name": "read_file", "input_schema": {"type": "object"}}],
    )
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "README.md"},
        schema_artifact_id=schema_id,
        validation={"status": "valid", "errors": []},
    )
    result_id = add_mcp_tool_result(
        builder,
        execution_id,
        content={"text": "# LumiAgent"},
        latency_ms=25,
    )
    consumption_id = add_mcp_result_consumption(
        builder,
        chain_id,
        consumed_artifact_ids=[result_id],
        consumption_summary="Agent read the README heading.",
        claimed_facts=["README starts with LumiAgent."],
    )
    builder.end_span(consumption_id, status=SpanStatus.SUCCESS, output={"status": "consumed"})
    builder.end_span(execution_id, status=SpanStatus.SUCCESS, output={"status": "success"})
    builder.end_span(chain_id, status=SpanStatus.SUCCESS)
    run = builder.build(status=RunStatus.SUCCESS)

    validate_run(run)
    chain = run.root_spans[0]
    execution = next(child for child in chain.children if child.span_id == execution_id)
    consumption = next(child for child in chain.children if child.span_id == consumption_id)
    discovery = next(
        child for child in chain.children if child.metadata["type"] == MCP_SPAN_DISCOVERY
    )
    assert chain.kind is SpanKind.CUSTOM
    assert chain.metadata["type"] == MCP_SPAN_TOOL_CHAIN
    assert discovery.artifacts[0].metadata["type"] == MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT
    assert execution.kind is SpanKind.TOOL
    assert execution.metadata["type"] == MCP_SPAN_TOOL_EXECUTION
    assert execution.input["schema_artifact_id"] == schema_id
    assert execution.artifacts[0].kind is ArtifactKind.TOOL_RESULT
    assert execution.artifacts[0].metadata["type"] == MCP_ARTIFACT_TOOL_RESULT
    assert consumption.metadata["type"] == MCP_SPAN_RESULT_CONSUMPTION



def test_mcp_helper_metadata_cannot_override_reserved_type() -> None:
    builder = TraceBuilder(run_id="run_mcp_metadata", name="MCP metadata")

    chain_id = start_mcp_tool_chain(
        builder,
        server_name="filesystem",
        metadata={"type": "custom", "note": "caller metadata"},
    )
    run = builder.build(status=RunStatus.SUCCESS)

    chain = run.root_spans[0]
    assert chain.span_id == chain_id
    assert chain.metadata["type"] == MCP_SPAN_TOOL_CHAIN
    assert chain.metadata["note"] == "caller metadata"

    builder = TraceBuilder(run_id="run_mcp_failure", name="MCP failure")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={},
        validation={"status": "invalid", "errors": [{"message": "path is required"}]},
    )
    event_id = add_mcp_failure_evidence(
        builder,
        execution_id,
        failure_type=McpFailureType.ARGUMENT_INVALID,
        failure_stage="argument_generation",
        server_name="filesystem",
        tool_name="read_file",
        call_span_id=execution_id,
        validation_errors=[{"message": "path is required"}],
    )
    builder.end_span(execution_id, status=SpanStatus.ERROR, output={"status": "error"})
    builder.end_span(chain_id, status=SpanStatus.ERROR)
    run = builder.build(status=RunStatus.ERROR)

    validate_run(run)
    event = run.root_spans[0].children[0].events[0]
    assert event.event_id == event_id
    assert event.name == "mcp_failure_evidence"
    assert event.metadata["failure_type"] == "argument_invalid"


def test_mcp_builder_records_initialization_and_tool_selection() -> None:
    builder = TraceBuilder(run_id="run_selection", name="selection demo")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    init_id = add_mcp_initialization(
        builder,
        chain_id,
        server_name="filesystem",
        protocol_version="2024-11-05",
        capabilities={"tools": True},
    )
    selection_id = add_mcp_tool_selection(
        builder,
        chain_id,
        server_name="filesystem",
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file"],
        reason="Tool name was provided by CLI.",
    )
    builder.end_span(chain_id)
    run = builder.build()

    validate_run(run)
    assert run.root_spans[0].children[0].metadata["type"] == MCP_SPAN_INITIALIZATION
    assert run.root_spans[0].children[1].metadata["type"] == MCP_SPAN_TOOL_SELECTION
    assert (
        run.root_spans[0].children[1].artifacts[0].metadata["type"]
        == MCP_ARTIFACT_TOOL_SELECTION
    )
    assert init_id != selection_id
