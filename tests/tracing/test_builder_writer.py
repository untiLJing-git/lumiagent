from lumiagent.tracing import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder_writer import BuilderTraceWriter


def test_builder_trace_writer_builds_run_incrementally() -> None:
    writer = BuilderTraceWriter()
    run_id = writer.start_run(name="Coding task", input_value={"task": "fix tests"})
    root_id = writer.start_span("Coding Agent Run", kind=SpanKind.CUSTOM)
    child_id = writer.start_span(
        "Run pytest",
        kind=SpanKind.TOOL,
        parent_span_id=root_id,
        input_value={"command": "python -m pytest -v"},
        metadata={"type": "test_run"},
    )

    event_id = writer.add_event(
        child_id,
        name="command_finished",
        level=EventLevel.INFO,
        message="pytest passed",
    )
    artifact_id = writer.add_artifact(
        child_id,
        name="Action Evidence",
        kind=ArtifactKind.JSON,
        content={"exit_code": 0},
        metadata={"type": "coding_action_evidence"},
    )
    writer.end_span(child_id, status=SpanStatus.SUCCESS, output={"exit_code": 0})
    writer.end_span(root_id, status=SpanStatus.SUCCESS)
    run = writer.flush(status=RunStatus.SUCCESS, output={"status": "success"})

    assert run.run_id == run_id
    assert run.root_spans[0].children[0].span_id == child_id
    assert run.root_spans[0].children[0].events[0].event_id == event_id
    assert run.root_spans[0].children[0].artifacts[0].artifact_id == artifact_id
    assert run.status == RunStatus.SUCCESS


def test_builder_trace_writer_requires_start_run_before_span() -> None:
    writer = BuilderTraceWriter()

    try:
        writer.start_span("orphan")
    except RuntimeError as exc:
        assert "start_run" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
