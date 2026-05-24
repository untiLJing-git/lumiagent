from datetime import datetime, timezone
from pathlib import Path

from lumiagent.tracing import AgentRun, RunStatus, Span, SpanKind, SpanStatus
from lumiagent.tracing.serializer import from_dict, from_json, to_dict, to_json
from lumiagent.tracing.validator import validate_run


FIXTURES = Path(__file__).parent / "fixtures"


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


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
