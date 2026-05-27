from datetime import UTC, datetime
from pathlib import Path

from lumiagent.tracing import (
    AgentRun,
    Annotation,
    RunStatus,
    Span,
    SpanKind,
    SpanStatus,
    TargetType,
)
from lumiagent.tracing.serializer import (
    from_dict,
    from_json,
    span_from_dict,
    span_from_json,
    span_to_dict,
    span_to_json,
    to_dict,
    to_json,
)
from lumiagent.tracing.validator import validate_run

FIXTURES = Path(__file__).parent / "fixtures"


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=UTC)


def make_run() -> AgentRun:
    root = Span(
        run_id="run_serialize",
        span_id="span_agent",
        name="Agent",
        kind=SpanKind.AGENT,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
    )
    return AgentRun(
        run_id="run_serialize",
        name="serialize demo",
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[root],
    )


def test_to_dict_uses_string_enums_and_iso_datetimes() -> None:
    data = to_dict(make_run())

    assert data["status"] == "success"
    assert data["started_at"] == "2026-05-24T12:00:00Z"
    assert data["root_spans"][0]["kind"] == "agent"


def test_json_round_trip_preserves_semantics() -> None:
    original = make_run()
    encoded = to_json(original)
    decoded = from_json(encoded)

    assert decoded.run_id == original.run_id
    assert decoded.status is RunStatus.SUCCESS
    assert decoded.root_spans[0].kind is SpanKind.AGENT
    assert decoded.root_spans[0].started_at == original.root_spans[0].started_at


def test_agent_run_linking_and_annotations_round_trip() -> None:
    original = make_run()
    original.parent_run_id = "run_parent"
    original.triggered_by_span_id = "span_agent"
    original.annotations.append(
        Annotation(
            annotation_id="annotation_serialize",
            target_type=TargetType.SPAN,
            target_id="span_agent",
            author="reviewer",
            note="Evidence looks correct.",
            evidence_span_ids=["span_agent"],
        )
    )

    decoded = from_json(to_json(original))

    assert decoded.parent_run_id == "run_parent"
    assert decoded.triggered_by_span_id == "span_agent"
    assert decoded.annotations[0].author == "reviewer"


def test_span_json_round_trip_preserves_semantics() -> None:
    original = make_run().root_spans[0]
    encoded = span_to_json(original)
    decoded = span_from_json(encoded)

    assert decoded.span_id == "span_agent"
    assert decoded.kind is SpanKind.AGENT
    assert span_from_dict(span_to_dict(original)).started_at == original.started_at


def test_from_dict_loads_agent_run() -> None:
    data = to_dict(make_run())
    decoded = from_dict(data)

    assert decoded.name == "serialize demo"
    assert decoded.root_spans[0].span_id == "span_agent"


def test_generic_agent_run_fixture_validates() -> None:
    run = from_json((FIXTURES / "generic_agent_run.json").read_text(encoding="utf-8"))
    validate_run(run)
    assert run.root_spans[0].children[0].kind is SpanKind.RAG


def test_coding_agent_trace_sample_fixture_validates() -> None:
    run = from_json((FIXTURES / "coding_agent_trace_sample.json").read_text(encoding="utf-8"))
    validate_run(run)
    operations = [child.metadata.get("operation") for child in run.root_spans[0].children]
    assert operations == ["file_search", "file_read", "code_edit", "shell_command", "test_run"]
