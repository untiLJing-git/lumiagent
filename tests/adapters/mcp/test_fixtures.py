from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lumiagent.adapters.mcp import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    McpFailureType,
)
from lumiagent.tracing.serializer import from_json
from lumiagent.tracing.validator import validate_run

if TYPE_CHECKING:
    from lumiagent.tracing.models import AgentRun, Event, Span

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> AgentRun:
    run = from_json((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    validate_run(run)
    return run


def _walk_spans(spans: list[Span]) -> list[Span]:
    flattened: list[Span] = []
    for span in spans:
        flattened.append(span)
        flattened.extend(_walk_spans(span.children))
    return flattened


def _all_events(run: AgentRun) -> list[Event]:
    events: list[Event] = []
    for span in _walk_spans(run.root_spans):
        events.extend(span.events)
    return events


def _failure_event(run: AgentRun, failure_type: McpFailureType) -> Event:
    return next(
        event
        for event in _all_events(run)
        if event.metadata.get("failure_type") == failure_type.value
    )


def test_success_fixture_contains_required_mcp_chain_evidence() -> None:
    run = _load_fixture("mcp_success_trace.json")

    spans = _walk_spans(run.root_spans)
    chain = run.root_spans[0]
    execution = next(
        span for span in spans if span.metadata.get("type") == MCP_SPAN_TOOL_EXECUTION
    )

    assert chain.metadata["type"] == MCP_SPAN_TOOL_CHAIN
    assert any(
        artifact.metadata.get("type") == MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT
        for span in spans
        for artifact in span.artifacts
    )
    assert any(
        artifact.metadata.get("type") == MCP_ARTIFACT_TOOL_RESULT
        for artifact in execution.artifacts
    )
    assert any(
        span.metadata.get("type") == MCP_SPAN_RESULT_CONSUMPTION for span in spans
    )


def test_argument_invalid_fixture_contains_schema_and_validation_evidence() -> None:
    run = _load_fixture("mcp_argument_invalid_trace.json")

    event = _failure_event(run, McpFailureType.ARGUMENT_INVALID)

    assert event.metadata["schema_artifact_id"] == "artifact_schema_argument_invalid"
    assert event.metadata["call_span_id"] == "span_argument_invalid_execution"
    assert event.metadata["validation_errors"]


def test_tool_execution_failed_fixture_contains_error_and_latency_evidence() -> None:
    run = _load_fixture("mcp_tool_execution_failed_trace.json")

    event = _failure_event(run, McpFailureType.TOOL_EXECUTION_FAILED)

    assert event.metadata["call_span_id"] == "span_execution_failed_execution"
    assert event.metadata["error_code"] == "EIO"
    assert event.metadata["latency_ms"] == 350


def test_result_misinterpreted_fixture_contains_consumption_evidence() -> None:
    run = _load_fixture("mcp_result_misinterpreted_trace.json")

    event = _failure_event(run, McpFailureType.RESULT_MISINTERPRETED)

    assert event.metadata["result_artifact_id"] == "artifact_result_misinterpreted"
    assert event.metadata["consumed_artifact_ids"] == ["artifact_result_misinterpreted"]
    assert event.metadata["contradicted_fields"] == ["content.files[0].path"]
    assert event.metadata["ignored_key_fields"] == ["content.files"]
