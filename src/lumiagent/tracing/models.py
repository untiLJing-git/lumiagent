"""Pydantic models for Agent trace data."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    ArtifactKind,
    EventLevel,
    RunStatus,
    Severity,
    SpanKind,
    SpanStatus,
    TargetType,
)

TraceValue = dict[str, Any] | list[Any] | str | int | float | bool | None


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class TimeRangeModel(BaseModel):
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> TimeRangeModel:
        if self.ended_at is not None and self.started_at > self.ended_at:
            raise ValueError("started_at must be before or equal to ended_at")
        return self


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("event"))
    name: str
    timestamp: datetime = Field(default_factory=utc_now)
    level: EventLevel = EventLevel.INFO
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class Artifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: new_id("artifact"))
    name: str
    kind: ArtifactKind = ArtifactKind.CUSTOM
    uri: str | None = None
    content: TraceValue = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def require_content_or_uri(self) -> Artifact:
        if self.uri is None and self.content is None:
            raise ValueError("artifact requires content or uri")
        return self


class Span(TimeRangeModel):
    span_id: str = Field(default_factory=lambda: new_id("span"))
    run_id: str
    parent_span_id: str | None = None
    name: str
    kind: SpanKind = SpanKind.CUSTOM
    status: SpanStatus = SpanStatus.PENDING
    input: TraceValue = None
    output: TraceValue = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    children: list[Span] = Field(default_factory=list)

    @field_validator("span_id", "run_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class Evaluation(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: new_id("eval"))
    target_type: TargetType
    target_id: str
    name: str
    score: float | None = None
    label: str | None = None
    reason: str = ""
    evidence_span_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evaluation_id", "target_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")
        return value


class Diagnosis(BaseModel):
    diagnosis_id: str = Field(default_factory=lambda: new_id("diag"))
    target_type: TargetType
    target_id: str
    failure_type: str
    severity: Severity = Severity.MEDIUM
    summary: str
    evidence_span_ids: list[str] = Field(default_factory=list)
    suggested_fix: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("diagnosis_id", "target_id", "failure_type", "summary", "suggested_fix")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class Annotation(BaseModel):
    annotation_id: str = Field(default_factory=lambda: new_id("annotation"))
    target_type: TargetType
    target_id: str
    author: str
    note: str
    label: str | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("annotation_id", "target_id", "author", "note")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class AgentRun(TimeRangeModel):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    name: str
    status: RunStatus = RunStatus.PENDING
    input: TraceValue = None
    output: TraceValue = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_run_id: str | None = None
    triggered_by_span_id: str | None = None
    root_spans: list[Span] = Field(default_factory=list)
    evaluations: list[Evaluation] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)

    @field_validator("run_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("parent_run_id", "triggered_by_span_id")
    @classmethod
    def require_non_empty_optional(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("value must not be empty")
        return value
