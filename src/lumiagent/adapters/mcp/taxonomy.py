"""MCP failure taxonomy."""

from __future__ import annotations

from enum import StrEnum


class McpFailureType(StrEnum):
    CONNECTION_FAILED = "connection_failed"
    DISCOVERY_FAILED = "discovery_failed"
    INITIALIZATION_FAILED = "initialization_failed"
    TOOL_DISCOVERY_FAILED = "tool_discovery_failed"
    SCHEMA_UNAVAILABLE = "schema_unavailable"
    SCHEMA_MISMATCH = "schema_mismatch"
    TOOL_SELECTION_WRONG = "tool_selection_wrong"
    TOOL_NOT_FOUND = "tool_not_found"
    ARGUMENT_GENERATION_FAILED = "argument_generation_failed"
    ARGUMENT_INVALID = "argument_invalid"
    PERMISSION_REQUIRED = "permission_required"
    PERMISSION_DENIED = "permission_denied"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TIMEOUT = "timeout"
    TRANSPORT_INTERRUPTED = "transport_interrupted"
    TOOL_RESULT_INVALID = "tool_result_invalid"
    RESULT_INVALID = "result_invalid"
    RESULT_MISINTERPRETED = "result_misinterpreted"
    INSUFFICIENT_RECOVERY_EVIDENCE = "insufficient_recovery_evidence"
    UNKNOWN = "unknown"
