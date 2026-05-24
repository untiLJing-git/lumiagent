"""Convenience builder for Agent traces."""
from __future__ import annotations

from typing import Any, Optional

from .enums import ArtifactKind, EventLevel, RunStatus, Severity, SpanKind, SpanStatus, TargetType
from .models import AgentRun, Artifact, Diagnosis, Event, Evaluation, Span, TraceValue, new_id, utc_now
from .validator import validate_run


class TraceBuilder:
    def __init__(self, *, run_id: Optional[str] = None, name: str, input: TraceValue = None) -> None:
        self.run = AgentRun(
            run_id=run_id or new_id("run"),
            name=name,
            status=RunStatus.RUNNING,
            input=input,
        )
        self._spans: dict[str, Span] = {}

    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.CUSTOM,
        parent_span_id: Optional[str] = None,
        input: TraceValue = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        if parent_span_id is not None and parent_span_id not in self._spans:
            raise ValueError(f"parent_span_id {parent_span_id} does not exist")

        span = Span(
            run_id=self.run.run_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            status=SpanStatus.RUNNING,
            input=input,
            metadata=metadata or {},
        )
        self._spans[span.span_id] = span

        if parent_span_id is None:
            self.run.root_spans.append(span)
        else:
            self._spans[parent_span_id].children.append(span)

        return span.span_id

    def end_span(
        self,
        span_id: str,
        *,
        status: SpanStatus = SpanStatus.SUCCESS,
        output: TraceValue = None,
    ) -> None:
        span = self._get_span(span_id)
        span.status = status
        span.output = output
        span.ended_at = utc_now()

    def add_event(
        self,
        span_id: str,
        *,
        name: str,
        level: EventLevel = EventLevel.INFO,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        span = self._get_span(span_id)
        event = Event(name=name, level=level, message=message, metadata=metadata or {})
        span.events.append(event)
        return event.event_id

    def add_artifact(
        self,
        span_id: str,
        *,
        name: str,
        kind: ArtifactKind = ArtifactKind.CUSTOM,
        content: TraceValue = None,
        uri: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        span = self._get_span(span_id)
        artifact = Artifact(name=name, kind=kind, content=content, uri=uri, metadata=metadata or {})
        span.artifacts.append(artifact)
        return artifact.artifact_id

    def add_evaluation(
        self,
        *,
        target_type: TargetType,
        target_id: str,
        name: str,
        score: Optional[float] = None,
        label: Optional[str] = None,
        reason: str = "",
        evidence_span_ids: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        evaluation = Evaluation(
            target_type=target_type,
            target_id=target_id,
            name=name,
            score=score,
            label=label,
            reason=reason,
            evidence_span_ids=evidence_span_ids or [],
            metadata=metadata or {},
        )
        self.run.evaluations.append(evaluation)
        return evaluation.evaluation_id

    def add_diagnosis(
        self,
        *,
        target_type: TargetType,
        target_id: str,
        failure_type: str,
        summary: str,
        evidence_span_ids: Optional[list[str]] = None,
        suggested_fix: str,
        severity: Severity = Severity.MEDIUM,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        diagnosis = Diagnosis(
            target_type=target_type,
            target_id=target_id,
            failure_type=failure_type,
            severity=severity,
            summary=summary,
            evidence_span_ids=evidence_span_ids or [],
            suggested_fix=suggested_fix,
            metadata=metadata or {},
        )
        self.run.diagnoses.append(diagnosis)
        return diagnosis.diagnosis_id

    def build(self, *, status: RunStatus = RunStatus.SUCCESS, output: TraceValue = None) -> AgentRun:
        self.run.status = status
        self.run.output = output
        self.run.ended_at = utc_now()
        validate_run(self.run)
        return self.run

    def _get_span(self, span_id: str) -> Span:
        if span_id not in self._spans:
            raise ValueError(f"span_id {span_id} does not exist")
        return self._spans[span_id]
