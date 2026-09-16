"""Normalize source-specific tool events into Coding Agent events."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Any

from lumiagent.adapters.coding.conventions import (
    CODING_APPROVAL_DECISION,
    CODING_CODE_EDIT,
    CODING_FILE_READ,
    CODING_FILE_SEARCH,
    CODING_GIT_DIFF,
    CODING_PERMISSION_REQUEST,
    CODING_SHELL_COMMAND,
    CODING_TEST_RUN,
    CODING_VERIFICATION,
)
from lumiagent.adapters.coding.events import (
    CodingActionEvidence,
    CodingStatus,
    NormalizedCodingEvent,
)

if TYPE_CHECKING:
    from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent


def normalize_hook_event(event: ClaudeCodeHookEvent) -> NormalizedCodingEvent:
    convention, parent, name, reason = _classify(event)
    status = _status(event)
    evidence = CodingActionEvidence(
        schema_version="coding_action_evidence.v2",
        tool_name=event.tool_name,
        server_name=_server_name(event),
        raw_result=event.payload.get("tool_response", event.payload.get("result")),
        schema_status="unverified" if event.payload.get("tool_schema") else "unavailable",
        arguments=_arguments(event.payload),
        result=_result(event.payload),
        safety=event.safety,
    )
    return NormalizedCodingEvent(
        event_id=f"coding_{event.event_id}",
        source_event_ids=[event.event_id],
        session_id=event.session_id,
        sequence=event.sequence,
        timestamp=event.timestamp,
        convention=convention,
        parent_convention=parent,
        status=status,
        name=name,
        action_evidence=evidence,
        metadata={"classification_reason": reason},
    )


def _classify(event: ClaudeCodeHookEvent) -> tuple[str, str | None, str, str]:
    tool_name = event.tool_name
    payload = event.payload
    if event.phase == "permission_request" or event.hook_name == "PermissionRequest":
        return (
            CODING_PERMISSION_REQUEST,
            None,
            "Request permission",
            "Claude Code permission request event",
        )
    if _is_denied_permission(payload):
        return (
            CODING_APPROVAL_DECISION,
            None,
            "Approval decision",
            "Claude Code permission denial event",
        )
    if _server_name(event) is not None or (tool_name or "").startswith("mcp__"):
        return "mcp_tool_execution", None, "Use MCP tool", "MCP identity; semantics not inferred"
    if tool_name in {"Glob", "Grep"}:
        return (
            CODING_FILE_SEARCH,
            "context_gathering",
            "Search files",
            f"{tool_name} maps to file_search",
        )
    if tool_name == "Read":
        return CODING_FILE_READ, "context_gathering", "Read file", "Read maps to file_read"
    if tool_name in {"Edit", "Write", "MultiEdit"}:
        return CODING_CODE_EDIT, None, "Edit code", f"{tool_name} maps to code_edit"
    if tool_name in {"Bash", "PowerShell"}:
        command = str(_arguments(payload).get("command", "")).strip().lower()
        if _is_test_command(command):
            return CODING_TEST_RUN, CODING_VERIFICATION, "Run tests", "command matched test pattern"
        if command.startswith("git diff"):
            return CODING_GIT_DIFF, None, "Inspect git diff", "command matched git diff"
        if _is_verification_command(command):
            return (
                CODING_VERIFICATION,
                None,
                "Run verification",
                "command matched verification pattern",
            )
        return CODING_SHELL_COMMAND, None, "Run shell command", "generic Bash command"
    return "tool_action", None, "Use tool", "unknown tool; not assumed to be a shell"


def _server_name(event: ClaudeCodeHookEvent) -> str | None:
    value = event.payload.get("server_name") or event.payload.get("mcp_server_name")
    if isinstance(value, str) and value:
        return value
    name = event.tool_name or ""
    parts = name.split("__", 2)
    return parts[1] if len(parts) == 3 and parts[0] == "mcp" and parts[1] else None


def _arguments(payload: dict[str, Any]) -> dict[str, Any]:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        return tool_input
    arguments = payload.get("arguments")
    if isinstance(arguments, dict):
        return arguments
    return {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "status",
            "duration_ms",
            "tool_response",
            "result",
            "tool_input",
            "arguments",
            "event_id",
            "session_id",
            "sequence",
            "event_index",
            "timestamp",
            "source",
            "tool_name",
            "tool_use_id",
            "call_id",
            "agent_id",
            "subagent_id",
            "phase",
            "hook_name",
            "hook_event_name",
            "cwd",
            "server_name",
            "mcp_server_name",
            "exit_code",
            "stdout_summary",
            "stderr_summary",
            "output_truncated",
            "decision",
            "permission_decision",
            "isError",
            "tool_schema",
        }
    }


def _result(payload: dict[str, Any]) -> dict[str, Any]:
    tool_response = payload.get("tool_response")
    if isinstance(tool_response, dict):
        return _flatten_tool_response(tool_response)
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    return {
        key: value
        for key, value in payload.items()
        if key
        in {
            "status",
            "exit_code",
            "duration_ms",
            "stdout_summary",
            "stderr_summary",
            "output_truncated",
        }
    }


def _status(event: ClaudeCodeHookEvent) -> CodingStatus:
    payload = event.payload
    if _is_denied_permission(payload) or event.phase == "error":
        return "error"
    result = _result(payload)
    raw = payload.get("tool_response", payload.get("result"))
    if (isinstance(raw, dict) and raw.get("isError") is True) or result.get("isError") is True:
        return "error"
    is_mcp = _server_name(event) is not None or (event.tool_name or "").startswith("mcp__")
    # Business data named status/exit_code inside an MCP result is not a protocol failure.
    exit_code = result.get("exit_code", payload.get("exit_code")) if not is_mcp else None
    if isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code != 0:
        return "error"
    status = payload.get("status")
    if status == "error":
        return "error"
    if status == "running":
        return "running"
    if status == "unknown":
        return "unknown"
    if event.phase in {"tool_request", "permission_request"}:
        return "unknown"
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        return "unknown"
    if status == "success":
        return "success"
    if event.phase == "tool_result" and result:
        return "success"
    return "unknown"


def _flatten_tool_response(tool_response: dict[str, Any]) -> dict[str, Any]:
    result = tool_response.get("result")
    if isinstance(result, dict):
        return {**tool_response, **result}
    return tool_response


def _is_denied_permission(payload: dict[str, Any]) -> bool:
    decision = str(payload.get("decision") or payload.get("permission_decision") or "").lower()
    return decision in {"deny", "denied", "block", "blocked"}


def _is_test_command(command: str) -> bool:
    tokens = _command_tokens(command)
    if not tokens:
        return False
    if _contains_sequence(tokens, ["python", "-m", "pytest"]):
        return True
    if any(token in {"pytest", "py.test"} for token in tokens):
        return True
    return any(
        tokens[index : index + 2][0] in {"npm", "pnpm", "yarn"}
        and tokens[index : index + 2][1] == "test"
        for index in range(len(tokens) - 1)
    )


def _contains_sequence(tokens: list[str], sequence: list[str]) -> bool:
    if len(tokens) < len(sequence):
        return False
    return any(
        tokens[index : index + len(sequence)] == sequence
        for index in range(len(tokens) - len(sequence) + 1)
    )


def _is_verification_command(command: str) -> bool:
    tokens = _command_tokens(command)
    if not tokens:
        return False
    if tokens[:3] == ["python", "-m", "mypy"]:
        return True
    return tokens[0] in {"ruff", "mypy", "pyright", "eslint", "tsc"}


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()
