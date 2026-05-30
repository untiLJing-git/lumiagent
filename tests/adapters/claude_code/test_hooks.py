from lumiagent.adapters.claude_code.hooks import build_hook_event


def test_build_hook_event_accepts_utf8_bom_prefix() -> None:
    event = build_hook_event({"session_id": "s1", "hook_event_name": "PreToolUse"})

    assert event.phase == "tool_request"


    pre = build_hook_event({"session_id": "s1", "hook_event_name": "PreToolUse"})
    post = build_hook_event({"session_id": "s1", "hook_event_name": "PostToolUse"})

    assert pre.phase == "tool_request"
    assert post.phase == "tool_result"


def test_build_hook_event_uses_claude_code_session_env(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "real-session")

    event = build_hook_event({"hook_event_name": "PreToolUse"})

    assert event.session_id == "real-session"


    event = build_hook_event({"session_id": "s1", "sequence": "not-a-number"})

    assert event.sequence == 1


def test_build_hook_event_uses_event_index_for_sequence() -> None:
    event = build_hook_event({"session_id": "s1", "event_index": 7})

    assert event.sequence == 7


def test_build_hook_event_writes_payload_fields() -> None:
    event = build_hook_event(
        {
            "session_id": "s1",
            "event_id": "evt_7",
            "tool_name": "Read",
            "cwd": "C:/repo",
            "hook_event_name": "PostToolUse",
            "tool_input": {"file_path": "src/app.py"},
        }
    )

    assert event.event_id == "evt_7"
    assert event.tool_name == "Read"
    assert event.working_directory == "C:/repo"
    assert event.payload["tool_input"] == {"file_path": "src/app.py"}


def test_build_hook_event_sanitizes_payload_fields() -> None:
    event = build_hook_event(
        {
            "session_id": "s1",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo token=secret-token"},
            "authorization": "Bearer abc.def.ghi",
        }
    )

    assert event.payload["tool_input"]["command"] == "echo token=[REDACTED]"
    assert event.payload["authorization"] == "[REDACTED]"
    assert event.safety == {"redaction_state": "redacted"}


