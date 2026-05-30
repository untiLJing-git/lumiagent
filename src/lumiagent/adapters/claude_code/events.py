"""Claude Code hook event schemas."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

HookPhase = Literal["tool_request", "tool_result", "permission_request", "error"]


class ClaudeCodeHookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "coding_hook_event.v1"
    event_id: str
    session_id: str
    sequence: int
    timestamp: str | None = None
    source: str = "claude_code_hook"
    hook_name: str
    tool_name: str | None = None
    phase: HookPhase
    working_directory: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=lambda: {"redaction_state": "raw"})


def read_hook_events(path: Path) -> list[ClaudeCodeHookEvent]:
    events: list[ClaudeCodeHookEvent] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        events.append(ClaudeCodeHookEvent.model_validate_json(line))
    return events


def write_hook_event(path: Path, event: ClaudeCodeHookEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
        handle.write("\n")
