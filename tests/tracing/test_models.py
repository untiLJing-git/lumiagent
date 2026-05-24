from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from lumiagent.tracing import (
    AgentRun,
    Artifact,
    ArtifactKind,
    Diagnosis,
    Event,
    EventLevel,
    Evaluation,
    RunStatus,
    Severity,
    Span,
    SpanKind,
    SpanStatus,
    TargetType,
)


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def test_create_agent_run_with_nested_span() -> None:
    child = Span(
        run_id="run_1",
        span_id="span_llm",
        parent_span_id="span_agent",
        name="Call model",
        kind=SpanKind.LLM,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        input={"messages": ["hello"]},
        output={"text": "world"},
    )
    root = Span(
        run_id="run_1",
        span_id="span_agent",
        parent_span_id=None,
        name="Agent workflow",
        kind=SpanKind.AGENT,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        children=[child],
    )
    run = AgentRun(
        run_id="run_1",
        name="demo run",
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[root],
    )

    assert run.run_id == "run_1"
    assert run.root_spans[0].children[0].kind is SpanKind.LLM
    assert run.root_spans[0].children[0].input == {"messages": ["hello"]}


def test_event_artifact_evaluation_and_diagnosis_models() -> None:
    event = Event(
        event_id="event_1",
        name="fallback_triggered",
        timestamp=utc_now(),
        level=EventLevel.WARNING,
        message="Primary provider failed.",
    )
    artifact = Artifact(
        artifact_id="artifact_1",
        name="prompt",
        kind=ArtifactKind.PROMPT,
        content="Hello",
    )
    evaluation = Evaluation(
        evaluation_id="eval_1",
        target_type=TargetType.RUN,
        target_id="run_1",
        name="quality",
        score=0.8,
        label="pass",
        reason="The answer is grounded.",
        evidence_span_ids=["span_llm"],
    )
    diagnosis = Diagnosis(
        diagnosis_id="diag_1",
        target_type=TargetType.RUN,
        target_id="run_1",
        failure_type="insufficient_verification",
        severity=Severity.MEDIUM,
        summary="The agent changed code without running tests.",
        evidence_span_ids=["span_edit"],
        suggested_fix="Run the relevant test command before finishing.",
    )

    assert event.level is EventLevel.WARNING
    assert artifact.kind is ArtifactKind.PROMPT
    assert evaluation.score == 0.8
    assert diagnosis.severity is Severity.MEDIUM


def test_score_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        Evaluation(
            evaluation_id="eval_bad",
            target_type=TargetType.RUN,
            target_id="run_1",
            name="quality",
            score=1.5,
            reason="Invalid score.",
        )


def test_artifact_requires_content_or_uri() -> None:
    with pytest.raises(ValidationError):
        Artifact(
            artifact_id="artifact_bad",
            name="empty",
            kind=ArtifactKind.CUSTOM,
        )


def test_ended_at_cannot_precede_started_at() -> None:
    with pytest.raises(ValidationError):
        Span(
            run_id="run_1",
            span_id="span_bad",
            name="Bad timing",
            kind=SpanKind.CUSTOM,
            status=SpanStatus.ERROR,
            started_at=datetime(2026, 5, 24, 12, 1, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
