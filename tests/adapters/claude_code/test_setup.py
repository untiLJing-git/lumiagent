import json
from pathlib import Path

import pytest

from lumiagent.adapters.claude_code.setup import (
    ClaudeCodeSettingsError,
    configure_claude_code_hooks,
    inspect_claude_code_hook_activation,
)


def test_configure_claude_code_hooks_creates_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"

    result = configure_claude_code_hooks(settings_path)

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert result.updated is True
    assert "hooks" in data
    assert "PostToolUse" in data["hooks"]
    assert "PostToolUseFailure" in data["hooks"]
    assert "PermissionRequest" in data["hooks"]


def test_configure_claude_code_hooks_preserves_existing_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(git status:*)"]}, "hooks": {"Stop": []}}),
        encoding="utf-8",
    )

    configure_claude_code_hooks(settings_path)

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["permissions"] == {"allow": ["Bash(git status:*)"]}
    assert "Stop" in data["hooks"]
    assert "PostToolUse" in data["hooks"]
    assert "PostToolUseFailure" in data["hooks"]
    assert "PermissionRequest" in data["hooks"]


def test_configure_claude_code_hooks_reports_not_in_claude_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("LUMIAGENT_SESSION_ID", raising=False)

    result = configure_claude_code_hooks(tmp_path / ".claude" / "settings.json")

    assert result.activation_status == "not_in_claude_code"
    assert result.session_id is None


def test_inspect_claude_code_hook_activation_reports_needs_reload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "session_1")

    result = inspect_claude_code_hook_activation(sessions_dir=tmp_path / "sessions")

    assert result.activation_status == "needs_reload"
    assert result.session_id == "session_1"
    assert result.events_path == tmp_path / "sessions" / "session_1" / "events.jsonl"
    assert "/hooks" in result.activation_hint


def test_inspect_claude_code_hook_activation_reports_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "session_1")
    events_path = tmp_path / "sessions" / "session_1" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    events_path.write_text("{}\n", encoding="utf-8")

    result = inspect_claude_code_hook_activation(sessions_dir=tmp_path / "sessions")

    assert result.activation_status == "active"
    assert result.events_path == events_path


def test_configure_claude_code_hooks_rejects_incompatible_hook_shapes(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"hooks": {"PreToolUse": {"bad": "shape"}}}),
        encoding="utf-8",
    )

    with pytest.raises(ClaudeCodeSettingsError, match="hooks.PreToolUse"):
        configure_claude_code_hooks(settings_path)

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["hooks"]["PreToolUse"] == {"bad": "shape"}
