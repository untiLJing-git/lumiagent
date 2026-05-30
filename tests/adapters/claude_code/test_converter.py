from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent


def test_converter_builds_hooks_only_coding_trace() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Read",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PostToolUse",
                tool_name="Edit",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_3",
                session_id="session_1",
                sequence=3,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "python -m pytest -v"}, "exit_code": 0},
            ),
        ],
    )

    assert run.name == "Claude Code session session_1"
    assert run.metadata["domain"] == "coding_agent"
    root = run.root_spans[0]
    child_types = [child.metadata.get("type") for child in root.children]
    assert "context_gathering" in child_types
    assert "code_edit" in child_types
    assert "verification" in child_types


def test_converter_adds_transcript_semantic_spans() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[],
        semantic_items=[
            {
                "item_id": "sem_1",
                "timestamp": "2026-05-30T00:00:00Z",
                "convention": "user_prompt",
                "role": "user",
                "content_summary": "Fix tests.",
                "content": "Fix tests.",
                "confidence": "high",
            }
        ],
    )

    root = run.root_spans[0]
    assert root.children[0].metadata["type"] == "user_prompt"
    assert root.children[0].metadata["source_item_ids"] == ["sem_1"]
    assert root.children[0].artifacts[0].metadata["type"] == "coding_semantic_evidence"


def test_converter_pairs_pre_and_post_tool_events_into_one_span() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PreToolUse",
                tool_name="Bash",
                phase="tool_request",
                payload={"tool_input": {"command": "python -m pytest -v"}},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"tool_response": {"exit_code": 0, "stdout_summary": "2 passed"}},
            ),
        ],
    )

    verification = next(
        child
        for child in run.root_spans[0].children
        if child.metadata.get("type") == "verification"
    )
    action_spans = [
        child for child in verification.children if child.metadata.get("type") == "test_run"
    ]
    assert len(action_spans) == 1
    assert action_spans[0].input == {"command": "python -m pytest -v"}
    assert action_spans[0].output == {"exit_code": 0, "stdout_summary": "2 passed"}
    assert action_spans[0].metadata["source_event_ids"] == ["evt_1", "evt_2"]


def test_converter_pairs_pre_and_post_tool_events_across_permission_request() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PreToolUse",
                tool_name="Bash",
                phase="tool_request",
                payload={"tool_input": {"command": "python -m pytest -v"}},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PermissionRequest",
                tool_name="Bash",
                phase="permission_request",
                payload={"tool_input": {"command": "python -m pytest -v"}},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_3",
                session_id="session_1",
                sequence=3,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"tool_response": {"exit_code": 0, "stdout_summary": "2 passed"}},
            ),
        ],
    )

    verification = next(
        child
        for child in run.root_spans[0].children
        if child.metadata.get("type") == "verification"
    )
    action_spans = [
        child for child in verification.children if child.metadata.get("type") == "test_run"
    ]
    assert len(action_spans) == 1
    assert action_spans[0].metadata["source_event_ids"] == ["evt_1", "evt_3"]


    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "pwd"}, "status": "running"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "pwd"}},
            ),
        ],
    )

    statuses = [child.status for child in run.root_spans[0].children]
    assert statuses[0].value == "running"
    assert statuses[1].value == "skipped"
    assert run.root_spans[0].status.value == "running"
    assert run.status.value == "running"


def test_converter_preserves_running_and_unknown_statuses() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "pwd"}, "status": "running"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "pwd"}},
            ),
        ],
    )

    statuses = [child.status for child in run.root_spans[0].children]
    assert statuses[0].value == "running"
    assert statuses[1].value == "skipped"
    assert run.root_spans[0].status.value == "running"
    assert run.status.value == "running"


    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "python -m pytest -v"}, "exit_code": 1},
            )
        ],
    )

    verification = run.root_spans[0].children[0]
    assert verification.status.value == "error"
    assert run.root_spans[0].status.value == "error"
    assert run.status.value == "error"


def test_converter_appends_workflow_check_span() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Edit",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            )
        ],
    )

    root = run.root_spans[0]
    workflow = next(
        child for child in root.children if child.metadata.get("type") == "workflow_check"
    )
    assert workflow.artifacts[0].metadata["type"] == "coding_workflow_checks"
    assert workflow.artifacts[0].content["status"] == "warning"


def test_converter_appends_passing_workflow_check_span() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Edit",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "python -m pytest -v"}, "exit_code": 0},
            ),
        ],
    )

    root = run.root_spans[0]
    workflow = next(
        child for child in root.children if child.metadata.get("type") == "workflow_check"
    )
    assert workflow.status.value == "success"
    assert workflow.artifacts[0].content["status"] == "pass"
    assert workflow.artifacts[0].content["findings"] == []
