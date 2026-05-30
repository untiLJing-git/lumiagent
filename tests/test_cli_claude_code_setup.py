from pathlib import Path

from typer.testing import CliRunner

from lumiagent.cli import app

runner = CliRunner()


def test_setup_claude_code_verify_reports_needs_reload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "session_1")
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["setup", "claude-code", "--verify"])

    assert result.exit_code == 0
    assert "Activation: needs_reload" in result.output
    assert "Open /hooks" in result.output


def test_setup_claude_code_verify_reports_active(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "session_1")
    with runner.isolated_filesystem(temp_dir=tmp_path):
        events_path = Path(".lumiagent") / "sessions" / "session_1" / "events.jsonl"
        events_path.parent.mkdir(parents=True)
        events_path.write_text("{}\n", encoding="utf-8")

        result = runner.invoke(app, ["setup", "claude-code", "--verify"])

    assert result.exit_code == 0
    assert "Activation: active" in result.output
    assert "Events path: .lumiagent" in result.output
