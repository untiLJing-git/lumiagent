from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.adapters.coding.normalizer import normalize_hook_event


def _event(tool_name: str, payload: dict[str, object]) -> ClaudeCodeHookEvent:
    return ClaudeCodeHookEvent(
        event_id="evt_1",
        session_id="session_1",
        sequence=1,
        hook_name="PostToolUse",
        tool_name=tool_name,
        phase="tool_result",
        payload=payload,
    )


def test_read_maps_to_file_read() -> None:
    normalized = normalize_hook_event(_event("Read", {"file_path": "src/app.py"}))

    assert normalized.convention == "file_read"
    assert normalized.name == "Read file"
    assert normalized.action_evidence is not None
    assert normalized.action_evidence.tool_name == "Read"


def test_grep_maps_to_file_search() -> None:
    normalized = normalize_hook_event(_event("Grep", {"pattern": "TraceWriter"}))

    assert normalized.convention == "file_search"


def test_edit_maps_to_code_edit() -> None:
    normalized = normalize_hook_event(_event("Edit", {"file_path": "src/app.py"}))

    assert normalized.convention == "code_edit"


def test_pytest_bash_maps_to_test_run() -> None:
    normalized = normalize_hook_event(
        _event(
            "Bash",
            {
                "arguments": {"command": "python -m pytest -v"},
                "exit_code": 0,
                "status": "success",
            },
        )
    )

    assert normalized.convention == "test_run"
    assert normalized.parent_convention == "verification"
    assert normalized.status == "success"


def test_powershell_pytest_maps_to_test_run() -> None:
    normalized = normalize_hook_event(
        _event(
            "PowerShell",
            {
                "tool_input": {
                    "command": '$env:PYTHONPATH = "src"; python -m pytest tests/adapters -v'
                },
                "tool_response": {"exit_code": 0, "stdout_summary": "11 passed"},
            },
        )
    )

    assert normalized.convention == "test_run"
    assert normalized.parent_convention == "verification"
    assert normalized.status == "success"


    normalized = normalize_hook_event(_event("Bash", {"arguments": {"command": "git diff"}}))

    assert normalized.convention == "git_diff"


def test_unknown_bash_maps_to_shell_command() -> None:
    normalized = normalize_hook_event(_event("Bash", {"arguments": {"command": "pwd"}}))

    assert normalized.convention == "shell_command"


def test_mentions_of_test_or_verification_tools_do_not_trigger_mapping() -> None:
    pytest_ini = normalize_hook_event(
        _event("Bash", {"arguments": {"command": "cat pytest.ini"}})
    )
    tsconfig = normalize_hook_event(
        _event("Bash", {"arguments": {"command": "cat tsconfig.json"}})
    )

    assert pytest_ini.convention == "shell_command"
    assert tsconfig.convention == "shell_command"


def test_claude_code_tool_input_maps_to_action_arguments() -> None:
    normalized = normalize_hook_event(
        _event(
            "Bash",
            {
                "tool_input": {"command": "python -m pytest -v"},
                "tool_response": {"exit_code": 0, "stdout_summary": "2 passed"},
            },
        )
    )

    assert normalized.convention == "test_run"
    assert normalized.status == "success"
    assert normalized.action_evidence is not None
    assert normalized.action_evidence.arguments == {"command": "python -m pytest -v"}
    assert normalized.action_evidence.result == {"exit_code": 0, "stdout_summary": "2 passed"}


def test_permission_request_maps_to_permission_request() -> None:
    normalized = normalize_hook_event(
        ClaudeCodeHookEvent(
            event_id="evt_1",
            session_id="session_1",
            sequence=1,
            hook_name="PermissionRequest",
            tool_name="Bash",
            phase="permission_request",
            payload={"tool_input": {"command": "git reset --hard"}},
        )
    )

    assert normalized.convention == "permission_request"
    assert normalized.name == "Request permission"


def test_denied_permission_result_maps_to_approval_decision_error() -> None:
    normalized = normalize_hook_event(
        ClaudeCodeHookEvent(
            event_id="evt_1",
            session_id="session_1",
            sequence=1,
            hook_name="PostToolUse",
            tool_name="Bash",
            phase="error",
            payload={"decision": "deny", "tool_input": {"command": "git reset --hard"}},
        )
    )

    assert normalized.convention == "approval_decision"
    assert normalized.status == "error"


