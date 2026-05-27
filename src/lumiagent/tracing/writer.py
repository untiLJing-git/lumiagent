"""Trace writer protocol for capture implementations."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .enums import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus

if TYPE_CHECKING:
    from .models import AgentRun, TraceValue


class TraceWriter(Protocol):
    def start_run(
        self,
        *,
        name: str,
        input_value: TraceValue = None,
        metadata: dict[str, object] | None = None,
    ) -> str: ...

    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.CUSTOM,
        parent_span_id: str | None = None,
        input_value: TraceValue = None,
        metadata: dict[str, object] | None = None,
    ) -> str: ...

    def end_span(
        self,
        span_id: str,
        *,
        status: SpanStatus = SpanStatus.SUCCESS,
        output: TraceValue = None,
    ) -> None: ...

    def add_event(
        self,
        span_id: str,
        *,
        name: str,
        level: EventLevel = EventLevel.INFO,
        message: str = "",
        metadata: dict[str, object] | None = None,
    ) -> str: ...

    def add_artifact(
        self,
        span_id: str,
        *,
        name: str,
        kind: ArtifactKind = ArtifactKind.CUSTOM,
        content: TraceValue = None,
        uri: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> str: ...

    def flush(
        self,
        *,
        status: RunStatus = RunStatus.SUCCESS,
        output: TraceValue = None,
    ) -> AgentRun: ...
