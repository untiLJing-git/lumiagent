from lumiagent.adapters.claude_code import ClaudeCodeHookEvent, ClaudeCodeTraceConverter
from lumiagent.adapters.coding import render_coding_trace_summary


def test_viewer_renders_workflow_checks_from_converted_edit_trace() -> None:
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

    lines = render_coding_trace_summary(run, show_checks=True)

    assert "Semantic Summary" in lines
    assert "Workflow Checks" in lines
    assert any("code_edit_requires_verification" in line for line in lines)
