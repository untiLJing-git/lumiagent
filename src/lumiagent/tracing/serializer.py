"""Serialization helpers for Agent traces."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .models import AgentRun, Span


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value.astimezone(UTC)
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def to_dict(run: AgentRun) -> dict[str, Any]:
    data = _to_jsonable(run.model_dump(mode="json"))
    if not isinstance(data, dict):
        raise TypeError("AgentRun serialization must produce a dictionary")
    return data


def to_json(run: AgentRun, *, indent: int = 2) -> str:
    return json.dumps(to_dict(run), ensure_ascii=False, indent=indent)


def from_dict(data: dict[str, Any]) -> AgentRun:
    return AgentRun.model_validate(data)


def from_json(data: str) -> AgentRun:
    return from_dict(json.loads(data))


def span_to_dict(span: Span) -> dict[str, Any]:
    data = _to_jsonable(span.model_dump(mode="json"))
    if not isinstance(data, dict):
        raise TypeError("Span serialization must produce a dictionary")
    return data


def span_to_json(span: Span, *, indent: int = 2) -> str:
    return json.dumps(span_to_dict(span), ensure_ascii=False, indent=indent)


def span_from_dict(data: dict[str, Any]) -> Span:
    return Span.model_validate(data)


def span_from_json(data: str) -> Span:
    return span_from_dict(json.loads(data))
