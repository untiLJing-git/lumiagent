"""Claude Code hook entrypoint."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lumiagent.adapters.claude_code.events import (
    ClaudeCodeHookEvent,
    HookPhase,
    session_events_path,
    write_hook_event,
)
from lumiagent.adapters.claude_code.sanitizer import sanitize_payload


def main() -> None:
    raw = sys.stdin.read().strip().lstrip("﻿")
    payload = json.loads(raw) if raw else {}
    event = build_hook_event(payload)
    write_hook_event(session_events_path(Path(".lumiagent") / "sessions", event.session_id), event)


def build_hook_event(payload: dict[str, Any]) -> ClaudeCodeHookEvent:
    session_id = str(
        _optional_str(payload.get("session_id"))
        or os.environ.get("LUMIAGENT_SESSION_ID")
        or os.environ.get("CLAUDE_CODE_SESSION_ID")
        or "default"
    )
    source_sequence = _source_sequence(payload)
    source_event_id = _optional_str(payload.get("event_id"))
    capture_id = f"capture_{uuid.uuid4().hex}"
    sanitized_payload = sanitize_payload(payload)
    return ClaudeCodeHookEvent(
        schema_version="coding_hook_event.v2",
        event_id=source_event_id or capture_id,
        capture_id=capture_id,
        source_event_id=source_event_id,
        source_sequence=source_sequence,
        call_id=_optional_str(payload.get("tool_use_id") or payload.get("call_id")),
        scope_id=_optional_str(payload.get("agent_id") or payload.get("subagent_id")) or "main",
        observed_at=datetime.now(UTC).isoformat(),
        session_id=session_id,
        sequence=source_sequence if source_sequence is not None else 1,
        timestamp=_optional_str(payload.get("timestamp")),
        hook_name=str(payload.get("hook_name") or payload.get("hook_event_name") or "unknown"),
        tool_name=_optional_str(payload.get("tool_name")),
        phase=_phase(payload.get("phase"), payload.get("hook_event_name")),
        working_directory=_optional_str(payload.get("cwd")),
        payload=sanitized_payload,
        safety={"redaction_state": "redacted"},
    )


def _source_sequence(payload: dict[str, Any]) -> int | None:
    for key in ("sequence", "event_index"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            continue
        try:
            sequence = int(value)
        except ValueError:
            continue
        if sequence >= 0:
            return sequence
    return None


def _phase(value: object, hook_event_name: object = None) -> HookPhase:
    if value == "tool_request":
        return "tool_request"
    if value == "permission_request":
        return "permission_request"
    if value == "error":
        return "error"
    if hook_event_name == "PreToolUse":
        return "tool_request"
    if hook_event_name == "PermissionRequest":
        return "permission_request"
    if hook_event_name == "PostToolUseFailure":
        return "error"
    return "tool_result"


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


if __name__ == "__main__":
    main()
