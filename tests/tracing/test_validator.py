from datetime import datetime, timezone

import pytest

from lumiagent.tracing import (
    AgentRun,
    Artifact,
    ArtifactKind,
    Diagnosis,
    Evaluation,
    RunStatus,
    Severity,
    Span,
    SpanKind,
    SpanStatus,
    TargetType,
)
from lumiagent.tracing.validator import TraceValidationError, validate_run


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def valid_run() -> AgentRun:
    llm = Span(
        run_id="run_valid",
        span_id="span_llm",
        parent_span_id="span_agent",
        name="LLM",
        kind=SpanKind.LLM,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        artifacts=[Artifact(artifact_id="artifact_prompt", name="prompt", kind=ArtifactKind.PROMPT, content="Hi")],
    )
    agent = Span(
        run_id="run_valid",
        span_id="span_agent",
        name="Agent",
        kind=SpanKind.AGENT,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        children=[llm],
    )
    return AgentRun(
        run_id="run_valid",
        name="valid run",
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[agent],
        evaluations=[
            Evaluation(
                evaluation_id="eval_valid",
                target_type=TargetType.RUN,
                target_id="run_valid",
                name="quality",
                score=1.0,
                reason="Valid trace.",
                evidence_span_ids=["span_llm"],
            )
        ],
        diagnoses=[
            Diagnosis(
                diagnosis_id="diag_valid",
                target_type=TargetType.RUN,
                target_id="run_valid",
                failure_type="unknown",
                severity=Severity.LOW,
                summary="No issue.",
                evidence_span_ids=["span_llm"],
                suggested_fix="No action needed.",
            )
        ],
    )


def test_valid_run_passes_validation() -> None:
    validate_run(valid_run())


def test_duplicate_span_id_fails_validation() -> None:
    run = valid_run()
    duplicate = Span(
        run_id="run_valid",
        span_id="span_llm",
        name="Duplicate",
        kind=SpanKind.TOOL,
    )
    run.root_spans.append(duplicate)

    with pytest.raises(TraceValidationError, match="Duplicate span_id"):
        validate_run(run)


def test_missing_parent_fails_validation() -> None:
    run = valid_run()
    run.root_spans.append(
        Span(
            run_id="run_valid",
            span_id="span_orphan",
            parent_span_id="span_missing",
            name="Orphan",
            kind=SpanKind.TOOL,
        )
    )

    with pytest.raises(TraceValidationError, match="parent_span_id"):
        validate_run(run)


def test_child_parent_mismatch_fails_validation() -> None:
    run = valid_run()
    run.root_spans[0].children[0].parent_span_id = "span_wrong"

    with pytest.raises(TraceValidationError, match="parent mismatch"):
        validate_run(run)


def test_evaluation_evidence_must_exist() -> None:
    run = valid_run()
    run.evaluations[0].evidence_span_ids = ["span_missing"]

    with pytest.raises(TraceValidationError, match="evidence span"):
        validate_run(run)


def test_diagnosis_target_must_exist() -> None:
    run = valid_run()
    run.diagnoses[0].target_id = "span_missing"
    run.diagnoses[0].target_type = TargetType.SPAN

    with pytest.raises(TraceValidationError, match="target_id"):
        validate_run(run)
