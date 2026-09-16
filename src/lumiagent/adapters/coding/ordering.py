"""Partial source order, independent of semantic tree structure or import time."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from lumiagent.tracing import Span

Relation = Literal["before", "after", "concurrent", "unknown"]


class SourcePosition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    scope_id: str = "main"
    sequence_start: int | None = Field(default=None, strict=True, ge=0)
    sequence_end: int | None = Field(default=None, strict=True, ge=0)
    started_at: str | None = None
    ended_at: str | None = None


def source_position(span: Span) -> SourcePosition | None:
    try:
        position = SourcePosition.model_validate(span.metadata.get("source_order"))
        if (
            position.sequence_start is not None
            and position.sequence_end is not None
            and position.sequence_end < position.sequence_start
        ):
            return None
        return position
    except (ValidationError, TypeError):
        return None


def parse_source_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None


def _range_relation(a0: float, a1: float, b0: float, b1: float) -> Relation:
    if a1 < a0 or b1 < b0:
        return "unknown"
    if a1 < b0:
        return "before"
    if b1 < a0:
        return "after"
    if a0 < b1 and b0 < a1:
        return "concurrent"
    return "unknown"


def source_relation(a: Span, b: Span) -> Relation:
    left, right = source_position(a), source_position(b)
    if left is None or right is None or left.session_id != right.session_id:
        return "unknown"
    relations: list[Relation] = []
    seq = (left.sequence_start, left.sequence_end, right.sequence_start, right.sequence_end)
    if left.scope_id == right.scope_id and all(
        isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in seq
    ):
        values = [n for n in seq if n is not None]
        relation = _range_relation(*values)
        if relation != "unknown":
            relations.append(relation)
    times = [
        parse_source_time(t)
        for t in (left.started_at, left.ended_at, right.started_at, right.ended_at)
    ]
    if all(t is not None for t in times):
        seconds = [t.timestamp() for t in times if t is not None]
        relation = _range_relation(*seconds)
        if relation != "unknown":
            relations.append(relation)
    return relations[0] if relations and len(set(relations)) == 1 else "unknown"


def source_duration_ms(span: Span) -> float | None:
    position = source_position(span)
    if position is None:
        return None
    start, end = parse_source_time(position.started_at), parse_source_time(position.ended_at)
    if start is None or end is None or end < start:
        return None
    # Point observations are not measured action durations.
    if span.metadata.get("observation_only"):
        return None
    return (end - start).total_seconds() * 1000


def flatten_spans(roots: list[Span]) -> list[Span]:
    return [s for root in roots for s in [root, *flatten_spans(root.children)]]
