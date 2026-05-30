"""Claude Code hook setup helpers."""
from __future__ import annotations

import json
import os
import pathlib  # noqa: TC003
from typing import Literal

from pydantic import BaseModel

ActivationStatus = Literal["active", "needs_reload", "not_in_claude_code"]


class ClaudeCodeSettingsError(ValueError):
    pass


class ClaudeCodeSetupResult(BaseModel):
    settings_path: pathlib.Path
    updated: bool
    configured_hooks: list[str]
    session_id: str | None = None
    events_path: pathlib.Path | None = None
    activation_status: ActivationStatus
    activation_hint: str


def configure_claude_code_hooks(settings_path: pathlib.Path) -> ClaudeCodeSetupResult:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    hooks = data.get("hooks")
    if hooks is None:
        hooks = {}
        data["hooks"] = hooks
    elif not isinstance(hooks, dict):
        raise ClaudeCodeSettingsError("hooks must be a JSON object")
    configured: list[str] = []
    command = "python -m lumiagent.adapters.claude_code.hooks"
    for hook_name in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"):
        entries = hooks.get(hook_name)
        if entries is None:
            entries = []
            hooks[hook_name] = entries
        elif not isinstance(entries, list):
            raise ClaudeCodeSettingsError(f"hooks.{hook_name} must be a list")
        entry = {"matcher": "*", "hooks": [{"type": "command", "command": command}]}
        if entry not in entries:
            entries.append(entry)
            configured.append(hook_name)
    settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    activation = inspect_claude_code_hook_activation()
    return ClaudeCodeSetupResult(
        settings_path=settings_path,
        updated=bool(configured),
        configured_hooks=configured,
        session_id=activation.session_id,
        events_path=activation.events_path,
        activation_status=activation.activation_status,
        activation_hint=activation.activation_hint,
    )


def inspect_claude_code_hook_activation(
    *,
    sessions_dir: pathlib.Path = pathlib.Path(".lumiagent/sessions"),
) -> ClaudeCodeSetupResult:
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get(
        "LUMIAGENT_SESSION_ID"
    )
    if not session_id:
        return ClaudeCodeSetupResult(
            settings_path=pathlib.Path(".claude/settings.json"),
            updated=False,
            configured_hooks=[],
            activation_status="not_in_claude_code",
            activation_hint=(
                "Not running inside a Claude Code session; runtime hook activation "
                "cannot be checked."
            ),
        )
    events_path = sessions_dir / session_id / "events.jsonl"
    if events_path.exists() and events_path.stat().st_size > 0:
        status: ActivationStatus = "active"
        hint = "Hooks are active for this Claude Code session."
    else:
        status = "needs_reload"
        hint = (
            "Hooks are configured, but this running Claude Code session has not "
            "captured events yet. Open /hooks and close it, or restart Claude Code, "
            "then run any tool call and verify again."
        )
    return ClaudeCodeSetupResult(
        settings_path=pathlib.Path(".claude/settings.json"),
        updated=False,
        configured_hooks=[],
        session_id=session_id,
        events_path=events_path,
        activation_status=status,
        activation_hint=hint,
    )
