"""Best-effort Claude Code transcript enrichment."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from lumiagent.adapters.coding.conventions import (
    CODING_FINAL_RESPONSE,
    CODING_TASK_UNDERSTANDING,
    CODING_USER_PROMPT,
)

if TYPE_CHECKING:
    from pathlib import Path


class TranscriptSemanticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    timestamp: str | None = None
    convention: str
    role: str
    content_summary: str
    content: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class TranscriptEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "coding_transcript_enrichment.v1"
    session_id: str
    source: str = "claude_code_transcript"
    source_path: str | None = None
    status: Literal["success", "unsupported"]
    items: list[TranscriptSemanticItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def enrich_transcript(path: Path, *, session_id: str) -> TranscriptEnrichment:
    if not path.exists():
        return TranscriptEnrichment(
            session_id=session_id,
            source_path=str(path),
            status="unsupported",
            warnings=["Transcript not found."],
        )
    try:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as exc:
        return TranscriptEnrichment(
            session_id=session_id,
            source_path=str(path),
            status="unsupported",
            warnings=[f"Transcript could not be parsed: {exc}"],
        )

    items: list[TranscriptSemanticItem] = []
    normalized_rows = [_normalize_row(row) for row in rows if isinstance(row, dict)]
    user_rows = [
        row
        for row in normalized_rows
        if row.get("role") == "user" and isinstance(row.get("content"), str)
    ]
    assistant_rows = [
        row
        for row in normalized_rows
        if row.get("role") == "assistant" and isinstance(row.get("content"), str)
    ]
    if user_rows:
        content = str(user_rows[0]["content"])
        items.append(
            TranscriptSemanticItem(
                item_id="sem_user_prompt_1",
                timestamp=_timestamp(user_rows[0]),
                convention=CODING_USER_PROMPT,
                role="user",
                content_summary=_summary(content),
                content=content,
                confidence="high",
            )
        )
    if assistant_rows:
        first = str(assistant_rows[0]["content"])
        items.append(
            TranscriptSemanticItem(
                item_id="sem_task_understanding_1",
                timestamp=_timestamp(assistant_rows[0]),
                convention=CODING_TASK_UNDERSTANDING,
                role="assistant",
                content_summary=_summary(first),
                content=first,
                confidence="medium",
            )
        )
        final_row = next(
            (row for row in reversed(assistant_rows) if row.get("final") is True),
            assistant_rows[-1],
        )
        final = str(final_row["content"])
        if final != first or len(assistant_rows) == 1:
            items.append(
                TranscriptSemanticItem(
                    item_id="sem_final_response_1",
                    timestamp=_timestamp(final_row),
                    convention=CODING_FINAL_RESPONSE,
                    role="assistant",
                    content_summary=_summary(final),
                    content=final,
                    confidence="high",
                )
            )
    return TranscriptEnrichment(
        session_id=session_id,
        source_path=str(path),
        status="success" if items else "unsupported",
        items=items,
        warnings=[] if items else ["No supported transcript messages found."],
    )


def _normalize_row(row: dict[str, object]) -> dict[str, object]:
    message = row.get("message")
    if isinstance(message, dict):
        role = message.get("role", row.get("role") or row.get("type"))
        content = _content_text(message.get("content"))
        return {
            "role": role,
            "content": content,
            "final": row.get("final", message.get("final")),
            "timestamp": row.get("timestamp", message.get("timestamp")),
        }
    return {
        "role": row.get("role", row.get("type")),
        "content": _content_text(row.get("content")),
        "final": row.get("final"),
        "timestamp": row.get("timestamp"),
    }


def _content_text(content: object) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
        if parts:
            return "\n".join(parts)
    return None


def _timestamp(row: dict[str, object]) -> str | None:
    timestamp = row.get("timestamp")
    if isinstance(timestamp, str):
        return timestamp
    return None


def _summary(content: str, *, limit: int = 160) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."
