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
        tool_name=event.tool_name,
        arguments=_arguments(event.payload),
        result=_result(event.payload),
        safety=event.safety,
    )
    source_event_ids = event.payload.get("_source_event_ids")
    return NormalizedCodingEvent(
        event_id=f"coding_{event.event_id}",
        source_event_ids=(
            [str(item) for item in source_event_ids]
            if isinstance(source_event_ids, list)
            else [event.event_id]
        ),
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
    return CODING_SHELL_COMMAND, None, "Use tool", "fallback tool mapping"


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
        if key not in {"status", "duration_ms", "tool_response", "result"}
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
    if _is_denied_permission(payload):
        return "error"
    status = payload.get("status")
    if status == "success":
        return "success"
    if status == "error":
        return "error"
    if status == "running":
        return "running"
    if status == "unknown":
        return "unknown"
    result = _result(payload)
    exit_code = result.get("exit_code", payload.get("exit_code"))
    if exit_code not in {None, 0}:
        return "error"
    if event.phase == "tool_result" and result:
        return "success"
    return "unknown"


def _flatten_tool_response(tool_response: dict[str, Any]) -> dict[str, Any]:
    result = tool_response.get("result")
    if isinstance(result, dict):
        return result
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
