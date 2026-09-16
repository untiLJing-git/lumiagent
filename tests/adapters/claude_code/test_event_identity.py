from pathlib import Path

import pytest
from pydantic import ValidationError

from lumiagent.adapters.claude_code.events import (
    ClaudeCodeHookEvent,
    read_hook_events,
    write_hook_event,
)
from lumiagent.adapters.claude_code.hooks import build_hook_event


def test_missing_source_identity_does_not_reuse_evt_1() -> None:
    a = build_hook_event({"session_id": "s", "tool_name": "Read"})
    b = build_hook_event({"session_id": "s", "tool_name": "Read"})
    assert a.event_id != b.event_id
    assert a.capture_id != b.capture_id
    assert a.source_event_id is None
    assert a.source_sequence is None
    assert a.schema_version == "coding_hook_event.v2"


def test_ingestion_order_is_not_source_order() -> None:
    event = build_hook_event({"sequence": "bad", "session_id": "s"})
    assert event.sequence == 1  # compatibility field, not reliable source order
    assert event.source_sequence is None
    assert event.observed_at is not None
    assert event.timestamp is None


def test_explicit_source_identity_and_scope_are_preserved() -> None:
    event = build_hook_event(
        {
            "session_id": "s",
            "event_id": "e",
            "event_index": 7,
            "tool_use_id": "c",
            "agent_id": "child",
        }
    )
    assert event.event_id == event.source_event_id == "e"
    assert event.source_sequence == 7
    assert event.call_id == "c"
    assert event.scope_id == "child"


def test_redaction_preserves_call_identity() -> None:
    event = build_hook_event(
        {
            "session_id": "s",
            "tool_use_id": "call_1",
            "tool_input": {"token": "secret", "file_path": "a.py"},
        }
    )
    assert event.call_id == "call_1"
    assert event.payload["tool_use_id"] == "call_1"
    assert event.payload["tool_input"]["token"] == "[REDACTED]"


def test_legacy_events_remain_readable(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"event_id":"evt_1","sequence":1,"session_id":"s",'
        '"hook_name":"PostToolUse","phase":"tool_result"}\n',
        encoding="utf-8",
    )
    first = read_hook_events(path)[0]
    second = read_hook_events(path)[0]
    assert first.schema_version == "coding_hook_event.v1"
    assert first.source_sequence is None
    assert first.source_event_id is None
    assert first.capture_id == second.capture_id
    assert first.ingestion_index == 1


def test_v2_roundtrip_and_unsupported_version(tmp_path: Path) -> None:
    event = build_hook_event({"session_id": "s", "tool_use_id": "c"})
    path = tmp_path / "events.jsonl"
    write_hook_event(path, event)
    loaded = read_hook_events(path)[0]
    assert loaded.capture_id == event.capture_id
    assert loaded.call_id == "c"
    with pytest.raises(ValidationError):
        ClaudeCodeHookEvent.model_validate({**event.model_dump(), "schema_version": "v999"})


@pytest.mark.parametrize("value", [True, -1, "bad"])
def test_invalid_source_sequence_is_not_trusted(value: object) -> None:
    assert build_hook_event({"session_id": "s", "sequence": value}).source_sequence is None
