"""Claude Code hook event schemas."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

HookPhase = Literal["tool_request", "tool_result", "permission_request", "error"]


class ClaudeCodeHookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["coding_hook_event.v1", "coding_hook_event.v2"] = "coding_hook_event.v1"
    event_id: str
    session_id: str
    sequence: int
    # Legacy sequence is retained for reading v1, never promoted to source order.
    capture_id: str | None = None
    source_event_id: str | None = None
    source_sequence: int | None = Field(default=None, ge=0, strict=True)
    call_id: str | None = None
    scope_id: str = "main"
    observed_at: str | None = None
    ingestion_index: int | None = Field(default=None, ge=1)
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
    for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        event = ClaudeCodeHookEvent.model_validate_json(line)
        # Stable within this imported record; NOT a source identity for deduplication.
        digest = hashlib.sha256(f"{index}:{line}".encode()).hexdigest()
        events.append(
            event.model_copy(
                update={
                    "capture_id": event.capture_id or f"import_{digest}",
                    "ingestion_index": index,
                }
            )
        )
    return events


def write_hook_event(path: Path, event: ClaudeCodeHookEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
        handle.write("\n")


def session_events_path(root: Path, session_id: str) -> Path:
    """Resolve a single session beneath its configured root, including symlink checks."""
    if session_id in {"", ".", ".."} or any(c in session_id for c in "\\/:\x00"):
        raise ValueError("session_id must be a single safe path component")
    base = root.resolve()
    path = (base / session_id / "events.jsonl").resolve()
    if not path.is_relative_to(base):
        raise ValueError("session path escapes the configured session root")
    return path
