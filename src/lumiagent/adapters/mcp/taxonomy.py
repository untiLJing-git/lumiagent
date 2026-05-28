"""MCP failure taxonomy."""

from __future__ import annotations

from enum import StrEnum


class McpFailureType(StrEnum):
    CONNECTION_FAILED = "connection_failed"
    INITIALIZATION_FAILED = "initialization_failed"
    TOOL_DISCOVERY_FAILED = "tool_discovery_failed"
    TOOL_NOT_FOUND = "tool_not_found"
    ARGUMENT_INVALID = "argument_invalid"
    PERMISSION_DENIED = "permission_denied"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TIMEOUT = "timeout"
    TRANSPORT_INTERRUPTED = "transport_interrupted"
    RESULT_INVALID = "result_invalid"
    RESULT_MISINTERPRETED = "result_misinterpreted"
    UNKNOWN = "unknown"
