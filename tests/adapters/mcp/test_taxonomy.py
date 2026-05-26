from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_ARGUMENT_GENERATION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_PERMISSION,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_mcp_failure_type_values_are_stable() -> None:
    assert [item.value for item in McpFailureType] == [
        "connection_failed",
        "discovery_failed",
        "tool_not_found",
        "schema_unavailable",
        "schema_mismatch",
        "tool_selection_wrong",
        "argument_generation_failed",
        "argument_invalid",
        "permission_required",
        "permission_denied",
        "tool_execution_failed",
        "tool_timeout",
        "tool_result_invalid",
        "result_misinterpreted",
        "insufficient_recovery_evidence",
    ]


def test_mcp_convention_values_are_stable() -> None:
    assert MCP_SPAN_TOOL_CHAIN == "mcp_tool_chain"
    assert MCP_SPAN_CONNECTION == "mcp_connection"
    assert MCP_SPAN_DISCOVERY == "mcp_discovery"
    assert MCP_SPAN_TOOL_SELECTION == "mcp_tool_selection"
    assert MCP_SPAN_ARGUMENT_GENERATION == "mcp_argument_generation"
    assert MCP_SPAN_PERMISSION == "mcp_permission"
    assert MCP_SPAN_TOOL_EXECUTION == "mcp_tool_execution"
    assert MCP_SPAN_RESULT_CONSUMPTION == "mcp_result_consumption"
    assert MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT == "mcp_tool_schema_snapshot"
    assert MCP_ARTIFACT_TOOL_RESULT == "mcp_tool_result"
