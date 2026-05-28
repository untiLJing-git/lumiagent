from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_FAILURE_EVIDENCE,
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_ARTIFACT_TOOL_SELECTION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_INITIALIZATION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_mcp_failure_type_values_are_stable() -> None:
    assert [item.value for item in McpFailureType] == [
        "connection_failed",
        "initialization_failed",
        "tool_discovery_failed",
        "tool_not_found",
        "argument_invalid",
        "permission_denied",
        "tool_execution_failed",
        "timeout",
        "transport_interrupted",
        "result_invalid",
        "result_misinterpreted",
        "unknown",
    ]


def test_existing_mcp_failure_values_remain_available() -> None:
    assert McpFailureType.ARGUMENT_INVALID.value == "argument_invalid"
    assert McpFailureType.TOOL_EXECUTION_FAILED.value == "tool_execution_failed"
    assert McpFailureType.RESULT_MISINTERPRETED.value == "result_misinterpreted"


def test_mcp_convention_values_are_stable() -> None:
    assert MCP_SPAN_TOOL_CHAIN == "mcp_tool_chain"
    assert MCP_SPAN_CONNECTION == "mcp_connection"
    assert MCP_SPAN_INITIALIZATION == "mcp_initialization"
    assert MCP_SPAN_DISCOVERY == "mcp_discovery"
    assert MCP_SPAN_TOOL_SELECTION == "mcp_tool_selection"
    assert MCP_SPAN_TOOL_EXECUTION == "mcp_tool_execution"
    assert MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT == "mcp_tool_schema_snapshot"
    assert MCP_ARTIFACT_TOOL_SELECTION == "mcp_tool_selection"
    assert MCP_ARTIFACT_TOOL_RESULT == "mcp_tool_result"
    assert MCP_ARTIFACT_FAILURE_EVIDENCE == "mcp_failure_evidence"
