from lumiagent.tracing import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus, TargetType
from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.validator import validate_run


def test_builder_creates_nested_trace() -> None:
    builder = TraceBuilder(run_id="run_builder", name="builder demo", input_value={"task": "demo"})
    agent_id = builder.start_span("Agent", kind=SpanKind.AGENT)
    llm_id = builder.start_span(
        "LLM",
        kind=SpanKind.LLM,
        parent_span_id=agent_id,
        input_value={"prompt": "Hi"},
    )
    builder.add_artifact(llm_id, name="prompt", kind=ArtifactKind.PROMPT, content="Hi")
    builder.add_event(
        llm_id,
        name="token_budget_warning",
        level=EventLevel.WARNING,
        message="Budget is high.",
    )
    builder.end_span(llm_id, status=SpanStatus.SUCCESS, output={"text": "Hello"})
    builder.end_span(agent_id, status=SpanStatus.SUCCESS)
    builder.add_evaluation(
        target_type=TargetType.RUN,
        target_id="run_builder",
        name="quality",
        score=0.9,
        reason="Good trace.",
        evidence_span_ids=[llm_id],
    )
    builder.add_diagnosis(
        target_type=TargetType.RUN,
        target_id="run_builder",
        failure_type="unknown",
        summary="No issue.",
        evidence_span_ids=[llm_id],
        suggested_fix="No action needed.",
    )
    run = builder.build(status=RunStatus.SUCCESS, output={"answer": "done"})

    validate_run(run)
    assert run.status is RunStatus.SUCCESS
    assert run.root_spans[0].children[0].artifacts[0].kind is ArtifactKind.PROMPT
    assert run.evaluations[0].score == 0.9


def test_builder_rejects_unknown_parent_span() -> None:
    builder = TraceBuilder(run_id="run_builder", name="builder demo")

    try:
        builder.start_span("Bad child", kind=SpanKind.TOOL, parent_span_id="span_missing")
    except ValueError as exc:
        assert "parent_span_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
