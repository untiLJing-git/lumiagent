"""MCP adapter conventions for LumiAgent traces."""

from lumiagent.adapters.mcp.builder import (
    add_mcp_failure_evidence,
    add_mcp_result_consumption,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    start_mcp_tool_chain,
)
from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_FAILURE_EVIDENCE,
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_ARTIFACT_TOOL_SELECTION,
    MCP_SPAN_ARGUMENT_GENERATION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_INITIALIZATION,
    MCP_SPAN_PERMISSION,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from lumiagent.adapters.mcp.schemas import (
    McpFailureEvidence,
    McpResultConsumptionEvidence,
    McpToolCallInput,
    McpToolExecutionSummary,
    McpToolSchemaSnapshot,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType

__all__ = [
    "McpFailureEvidence",
    "McpFailureType",
    "McpResultConsumptionEvidence",
    "McpToolCallInput",
    "McpToolExecutionSummary",
    "McpToolSchemaSnapshot",
    "MCP_ARTIFACT_FAILURE_EVIDENCE",
    "MCP_ARTIFACT_TOOL_RESULT",
    "MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT",
    "MCP_ARTIFACT_TOOL_SELECTION",
    "MCP_SPAN_ARGUMENT_GENERATION",
    "MCP_SPAN_CONNECTION",
    "MCP_SPAN_DISCOVERY",
    "MCP_SPAN_INITIALIZATION",
    "MCP_SPAN_PERMISSION",
    "MCP_SPAN_RESULT_CONSUMPTION",
    "MCP_SPAN_TOOL_CHAIN",
    "MCP_SPAN_TOOL_EXECUTION",
    "MCP_SPAN_TOOL_SELECTION",
    "add_mcp_failure_evidence",
    "add_mcp_result_consumption",
    "add_mcp_tool_execution",
    "add_mcp_tool_result",
    "add_mcp_tool_schema_snapshot",
    "start_mcp_tool_chain",
]
