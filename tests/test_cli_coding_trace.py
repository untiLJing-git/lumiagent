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
    assert "Workflow checks: unknown" in result.output  # no v1 completeness evidence


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


def test_trace_rejects_session_path_traversal(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "events.jsonl").write_text("", encoding="utf-8")
    output = tmp_path / "out.json"
    result = runner.invoke(
        app, ["trace", "../outside", "-o", str(output), "--sessions-dir", str(sessions)]
    )
    assert result.exit_code != 0
    assert not output.exists()


def test_trace_reports_malformed_jsonl_without_uncaught_validation_error(tmp_path: Path) -> None:
    folder = tmp_path / "s"
    folder.mkdir()
    (folder / "events.jsonl").write_text("not-json", encoding="utf-8")
    result = runner.invoke(
        app, ["trace", "s", "-o", str(tmp_path / "out.json"), "--sessions-dir", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert "Invalid session" in result.output


def test_trace_never_overwrites_existing_output(tmp_path: Path) -> None:
    folder = tmp_path / "s"
    folder.mkdir()
    (folder / "events.jsonl").write_text("", encoding="utf-8")
    output = tmp_path / "out.json"
    output.write_text("keep", encoding="utf-8")
    result = runner.invoke(app, ["trace", "s", "-o", str(output), "--sessions-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert "overwrite" in result.output
    assert output.read_text(encoding="utf-8") == "keep"
