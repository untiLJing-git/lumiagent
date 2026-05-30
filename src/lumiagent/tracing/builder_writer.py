"""TraceWriter implementation backed by TraceBuilder."""
from __future__ import annotations

from typing import TYPE_CHECKING

from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.enums import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus

if TYPE_CHECKING:
    from lumiagent.tracing.models import AgentRun, TraceValue


class BuilderTraceWriter:
    def __init__(self) -> None:
        self._builder: TraceBuilder | None = None

    def start_run(
        self,
        *,
        name: str,
        input_value: TraceValue = None,
        metadata: dict[str, object] | None = None,
    ) -> str:
        self._builder = TraceBuilder(name=name, input_value=input_value)
        if metadata:
            self._builder.run.metadata.update(metadata)
        return self._builder.run.run_id

    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.CUSTOM,
        parent_span_id: str | None = None,
        input_value: TraceValue = None,
        metadata: dict[str, object] | None = None,
    ) -> str:
        return self._require_builder().start_span(
            name,
            kind=kind,
            parent_span_id=parent_span_id,
            input_value=input_value,
            metadata=dict(metadata or {}),
        )

    def end_span(
        self,
        span_id: str,
        *,
        status: SpanStatus = SpanStatus.SUCCESS,
        output: TraceValue = None,
    ) -> None:
        self._require_builder().end_span(span_id, status=status, output=output)

    def add_event(
        self,
        span_id: str,
        *,
        name: str,
        level: EventLevel = EventLevel.INFO,
        message: str = "",
        metadata: dict[str, object] | None = None,
    ) -> str:
        return self._require_builder().add_event(
            span_id,
            name=name,
            level=level,
            message=message,
            metadata=dict(metadata or {}),
        )

    def add_artifact(
        self,
        span_id: str,
        *,
        name: str,
        kind: ArtifactKind = ArtifactKind.CUSTOM,
        content: TraceValue = None,
        uri: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> str:
        return self._require_builder().add_artifact(
            span_id,
            name=name,
            kind=kind,
            content=content,
            uri=uri,
            metadata=dict(metadata or {}),
        )

    def flush(
        self,
        *,
        status: RunStatus = RunStatus.SUCCESS,
        output: TraceValue = None,
    ) -> AgentRun:
        return self._require_builder().build(status=status, output=output)

    def _require_builder(self) -> TraceBuilder:
        if self._builder is None:
            raise RuntimeError("start_run must be called before writing trace data")
        return self._builder
