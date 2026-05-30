from pathlib import Path

from lumiagent.adapters.claude_code.events import (
    ClaudeCodeHookEvent,
    read_hook_events,
    write_hook_event,
)


def test_hook_event_defaults_schema_and_source() -> None:
    event = ClaudeCodeHookEvent(
        event_id="evt_1",
        session_id="session_1",
        sequence=1,
        hook_name="PostToolUse",
        tool_name="Read",
        phase="tool_result",
        payload={"status": "success"},
    )

    assert event.schema_version == "coding_hook_event.v1"
    assert event.source == "claude_code_hook"
    assert event.safety == {"redaction_state": "raw"}


def test_read_hook_events_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        '﻿{"schema_version":"coding_hook_event.v1","event_id":"evt_1","session_id":"session_1","sequence":1,"hook_name":"PostToolUse","phase":"tool_result"}\n',
        encoding="utf-8",
    )

    events = read_hook_events(path)

    assert events[0].event_id == "evt_1"


def test_write_and_read_hook_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    write_hook_event(
        path,
        ClaudeCodeHookEvent(
            event_id="evt_1",
            session_id="session_1",
            sequence=1,
            hook_name="PreToolUse",
            tool_name="Bash",
            phase="tool_request",
            payload={"arguments": {"command": "python -m pytest -v"}},
        ),
    )

    events = read_hook_events(path)

    assert len(events) == 1
    assert events[0].event_id == "evt_1"
    assert events[0].payload["arguments"]["command"] == "python -m pytest -v"
