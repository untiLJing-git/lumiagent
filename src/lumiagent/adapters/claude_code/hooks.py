"""Claude Code hook entrypoint."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent, HookPhase, write_hook_event
from lumiagent.adapters.claude_code.sanitizer import sanitize_payload


def main() -> None:
    raw = sys.stdin.read().strip().lstrip("﻿")
    payload = json.loads(raw) if raw else {}
    event = build_hook_event(payload)
    write_hook_event(Path(".lumiagent") / "sessions" / event.session_id / "events.jsonl", event)


def build_hook_event(payload: dict[str, Any]) -> ClaudeCodeHookEvent:
    session_id = str(
        payload.get("session_id")
        or os.environ.get("LUMIAGENT_SESSION_ID")
        or os.environ.get("CLAUDE_CODE_SESSION_ID")
        or "default"
    )
    sequence = _sequence(payload)
    sanitized_payload = sanitize_payload(payload)
    return ClaudeCodeHookEvent(
        event_id=str(payload.get("event_id") or f"evt_{sequence}"),
        session_id=session_id,
        sequence=sequence,
        timestamp=_optional_str(payload.get("timestamp")),
        hook_name=str(payload.get("hook_name") or payload.get("hook_event_name") or "unknown"),
        tool_name=_optional_str(payload.get("tool_name")),
        phase=_phase(payload.get("phase"), payload.get("hook_event_name")),
        working_directory=_optional_str(payload.get("cwd")),
        payload=sanitized_payload,
        safety={"redaction_state": "redacted"},
    )


def _sequence(payload: dict[str, Any]) -> int:
    for key in ("sequence", "event_index"):
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 1


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
    if value is None:
        return None
    return str(value)


if __name__ == "__main__":
    main()
