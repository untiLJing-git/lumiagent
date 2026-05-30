import json
from pathlib import Path

from typer.testing import CliRunner

from lumiagent.cli import app

runner = CliRunner()


def test_trace_command_converts_session_events(tmp_path: Path) -> None:
    session_dir = tmp_path / ".lumiagent" / "sessions" / "session_1"
    session_dir.mkdir(parents=True)
    (session_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "coding_hook_event.v1",
                "event_id": "evt_1",
                "session_id": "session_1",
                "sequence": 1,
                "source": "claude_code_hook",
                "hook_name": "PostToolUse",
                "tool_name": "Edit",
                "phase": "tool_result",
                "payload": {"file_path": "src/app.py", "status": "success"},
                "safety": {"redaction_state": "raw"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "trace.json"

    result = runner.invoke(
        app,
        [
            "trace",
            "session_1",
            "-o",
            str(output),
            "--sessions-dir",
            str(tmp_path / ".lumiagent" / "sessions"),
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert "Workflow checks: warning" in result.output


def test_show_command_routes_coding_trace(tmp_path: Path) -> None:
    session_dir = tmp_path / ".lumiagent" / "sessions" / "session_1"
    session_dir.mkdir(parents=True)
    (session_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "coding_hook_event.v1",
                "event_id": "evt_1",
                "session_id": "session_1",
                "sequence": 1,
                "source": "claude_code_hook",
                "hook_name": "PostToolUse",
                "tool_name": "Edit",
                "phase": "tool_result",
                "payload": {"file_path": "src/app.py", "status": "success"},
                "safety": {"redaction_state": "raw"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "trace.json"
    runner.invoke(
        app,
        [
            "trace",
            "session_1",
            "-o",
            str(output),
            "--sessions-dir",
            str(tmp_path / ".lumiagent" / "sessions"),
        ],
    )

    result = runner.invoke(app, ["show", str(output), "--checks"])

    assert result.exit_code == 0
    assert "Semantic Summary" in result.output
    assert "Workflow Checks" in result.output
    assert "code_edit_requires_verification" in result.output
