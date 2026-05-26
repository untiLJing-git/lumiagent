"""MCP failure taxonomy."""

from __future__ import annotations

from enum import StrEnum


class McpFailureType(StrEnum):
    """Enumerates failure modes across the MCP tool chain lifecycle.

    The order follows the tool chain pipeline: connection -> discovery ->
    tool resolution -> argument generation -> permission -> execution ->
    result consumption -> recovery.
    """

    CONNECTION_FAILED = "connection_failed"
    DISCOVERY_FAILED = "discovery_failed"
    TOOL_NOT_FOUND = "tool_not_found"
    SCHEMA_UNAVAILABLE = "schema_unavailable"
    SCHEMA_MISMATCH = "schema_mismatch"
    TOOL_SELECTION_WRONG = "tool_selection_wrong"
    ARGUMENT_GENERATION_FAILED = "argument_generation_failed"
    ARGUMENT_INVALID = "argument_invalid"
    PERMISSION_REQUIRED = "permission_required"
    PERMISSION_DENIED = "permission_denied"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_RESULT_INVALID = "tool_result_invalid"
    RESULT_MISINTERPRETED = "result_misinterpreted"
    INSUFFICIENT_RECOVERY_EVIDENCE = "insufficient_recovery_evidence"
