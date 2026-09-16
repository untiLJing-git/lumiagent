import pytest

from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.hooks import build_hook_event
from lumiagent.adapters.coding.events import CaptureCapabilities
from lumiagent.adapters.coding.normalizer import normalize_hook_event
from lumiagent.adapters.coding.ordering import source_duration_ms, source_relation
from lumiagent.adapters.coding.validator import validate_coding_workflow
from lumiagent.tracing import Span


def point(n=None, **extra):
    position = {
        "session_id": "s",
        "scope_id": "main",
        "sequence_start": n,
        "sequence_end": n,
        **extra,
    }
    return Span(run_id="r", name="point", metadata={"source_order": position})


def test_partial_order_and_missing_timestamps() -> None:
    a, b = point(1), point(2)
    assert source_relation(a, b) == "before"
    assert source_relation(b, a) == "after"
    assert source_relation(a, point()) == "unknown"
    assert source_relation(a, point(2, scope_id="child")) == "unknown"
    assert source_relation(point(1, sequence_end=3), point(2, sequence_end=4)) == "concurrent"
    assert source_duration_ms(a) is None


def test_source_time_not_conversion_time() -> None:
    a = point(started_at="2026-05-30T00:00:00Z", ended_at="2026-05-30T00:00:02Z")
    assert source_duration_ms(a) == 2000
    assert source_duration_ms(point(started_at="bad", ended_at="bad")) is None
    assert (
        source_relation(
            a, point(started_at="2026-05-30T00:00:03Z", ended_at="2026-05-30T00:00:04Z")
        )
        == "before"
    )


def test_conflicting_sequence_and_time_is_unknown() -> None:
    a = point(1, started_at="2026-05-30T00:00:03Z", ended_at="2026-05-30T00:00:04Z")
    b = point(2, started_at="2026-05-30T00:00:01Z", ended_at="2026-05-30T00:00:02Z")
    assert source_relation(a, b) == "unknown"


def lifecycle(n, name, command, exit_code=0):
    call = f"call_{n}"
    return [
        build_hook_event(
            {
                "session_id": "s",
                "cwd": "C:/repo",
                "event_id": f"e{n}",
                "sequence": n,
                "tool_use_id": call,
                "tool_name": name,
                "phase": "tool_request",
                "tool_input": command,
            }
        ),
        build_hook_event(
            {
                "session_id": "s",
                "cwd": "C:/repo",
                "event_id": f"e{n + 1}",
                "sequence": n + 1,
                "tool_use_id": call,
                "tool_name": name,
                "phase": "tool_result",
                "tool_response": {"exit_code": exit_code},
            }
        ),
    ]


def test_test_edit_retest_uses_source_order_not_grouping() -> None:
    events = (
        lifecycle(1, "Bash", {"command": "pytest"}, 1)
        + lifecycle(3, "Edit", {"file_path": "a.py"})
        + lifecycle(5, "Bash", {"command": "pytest"})
    )
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=events,
        coverage=CaptureCapabilities(
            workflow_coverage="complete", coverage_basis="controlled test"
        ),
    )
    result = validate_coding_workflow(run)
    assert result.status == "pass"
    assert result.findings == []
    assert run.evaluations == [] and run.diagnoses == []


def test_incomplete_capture_does_not_prove_missing_verification() -> None:
    run = ClaudeCodeTraceConverter().convert(session_id="s", events=lifecycle(1, "Edit", {}))
    result = validate_coding_workflow(run)
    assert result.status == "unknown"
    assert result.findings[0].status == "unknown"


def test_complete_capture_can_find_missing_verification() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=lifecycle(1, "Edit", {}),
        coverage=CaptureCapabilities(
            workflow_coverage="complete", coverage_basis="controlled test"
        ),
    )
    assert validate_coding_workflow(run).status == "warning"


def test_final_response_keeps_source_timestamp() -> None:
    rows = lifecycle(1, "Bash", {"command": "pytest"})
    rows[0].timestamp = "2026-05-30T00:00:01Z"
    rows[1].timestamp = "2026-05-30T00:00:02Z"
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=rows,
        semantic_items=[
            {
                "item_id": "final",
                "timestamp": "2026-05-30T00:00:03Z",
                "convention": "final_response",
                "role": "assistant",
                "content_summary": "Done",
                "confidence": "high",
            }
        ],
    )
    root = run.root_spans[0]
    action = next(s for g in root.children for s in g.children if s.kind.value == "tool")
    final = next(s for s in root.children if s.metadata.get("type") == "final_response")
    assert source_relation(action, final) == "before"
    assert final.metadata["timestamp_basis"] == "ingestion"
    assert run.metadata["capture_capabilities"]["workflow_coverage"] != "complete"


def test_unknown_mcp_preserves_raw_result_and_identity() -> None:
    row = build_hook_event(
        {
            "session_id": "s",
            "tool_name": "mcp__files__read_file",
            "tool_use_id": "c",
            "phase": "tool_result",
            "tool_response": ["one", "two"],
            "tool_input": {"path": "a.py"},
        }
    )
    normalized = normalize_hook_event(row)
    assert normalized.convention == "mcp_tool_execution"
    assert normalized.action_evidence.server_name == "files"
    assert normalized.action_evidence.schema_status == "unavailable"
    assert normalized.action_evidence.raw_result == ["one", "two"]
    assert normalized.action_evidence.tool_name == "mcp__files__read_file"


@pytest.mark.parametrize("raw", [{"isError": True}, {"status": "error"}])
def test_result_error_is_not_silently_success(raw) -> None:
    row = build_hook_event(
        {
            "session_id": "s",
            "tool_name": "mcp__files__read_file",
            "phase": "error",
            "tool_response": raw,
        }
    )
    assert normalize_hook_event(row).status == "error"


@pytest.mark.parametrize("invalid", [True, "1", -1])
def test_malformed_source_sequence_is_not_coerced(invalid) -> None:
    assert source_relation(point(invalid), point(2)) == "unknown"


def test_large_source_sequences_keep_integer_precision() -> None:
    assert source_relation(point(2**60), point(2**60 + 1)) == "before"


def test_verification_in_another_scope_does_not_satisfy_edit() -> None:
    edits = lifecycle(1, "Edit", {"file_path": "a.py"})
    tests = lifecycle(3, "Bash", {"command": "pytest"})
    for i, row in enumerate(edits + tests):
        row.timestamp = f"2026-05-30T00:00:0{i + 1}Z"
    for row in tests:
        row.scope_id = "another_agent"
        row.payload["agent_id"] = "another_agent"
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=edits + tests,
        coverage=CaptureCapabilities(workflow_coverage="complete", coverage_basis="controlled"),
    )
    assert validate_coding_workflow(run).status != "pass"


def test_verification_still_running_is_not_a_proven_absence() -> None:
    edits = lifecycle(1, "Edit", {})
    tests = lifecycle(3, "Bash", {"command": "pytest"})
    tests[1].payload["status"] = "running"
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=edits + tests,
        coverage=CaptureCapabilities(workflow_coverage="complete", coverage_basis="controlled"),
    )
    assert validate_coding_workflow(run).status == "unknown"


def test_capability_claims_without_collected_evidence_are_not_inherited() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=lifecycle(1, "Read", {}),
        coverage=CaptureCapabilities(costs="available", final_state="available"),
    )
    assert run.metadata["capture_capabilities"]["costs"] == "unknown"
    assert run.metadata["capture_capabilities"]["final_state"] == "unknown"


def test_truncated_result_is_reported_as_a_gap() -> None:
    rows = lifecycle(1, "Bash", {"command": "pytest"})
    rows[1].payload["tool_response"]["output_truncated"] = True
    run = ClaudeCodeTraceConverter().convert(session_id="s", events=rows)
    assert "tool_result_truncated" in run.metadata["capture_capabilities"]["gaps"]


def test_conflicting_success_and_exit_code_uses_error_evidence() -> None:
    row = build_hook_event(
        {
            "session_id": "s",
            "phase": "tool_result",
            "status": "success",
            "tool_name": "Bash",
            "tool_response": {"exit_code": 1},
        }
    )
    assert normalize_hook_event(row).status == "error"


def test_outer_mcp_error_cannot_be_overwritten_by_nested_result() -> None:
    row = build_hook_event(
        {
            "session_id": "s",
            "phase": "tool_result",
            "tool_name": "mcp__a__b",
            "tool_response": {"isError": True, "result": {"isError": False}},
        }
    )
    assert normalize_hook_event(row).status == "error"


def test_mcp_business_error_field_is_not_a_protocol_error() -> None:
    row = build_hook_event(
        {
            "session_id": "s",
            "tool_name": "mcp__db__read",
            "phase": "tool_result",
            "tool_response": {"isError": False, "result": {"status": "error", "exit_code": 5}},
        }
    )
    assert normalize_hook_event(row).status == "success"


def test_unrelated_retry_in_another_directory_is_not_recovery() -> None:
    rows = lifecycle(1, "Bash", {"command": "pytest"}, 1)
    retry = lifecycle(3, "Bash", {"command": "pytest"})
    for event in retry:
        event.working_directory = "C:/other"
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=rows + retry,
        coverage=CaptureCapabilities(workflow_coverage="complete", coverage_basis="controlled"),
    )
    assert validate_coding_workflow(run).status == "error"


def test_reversed_source_interval_is_not_marked_available() -> None:
    rows = lifecycle(3, "Read", {})
    rows[1].source_sequence = 1
    run = ClaudeCodeTraceConverter().convert(session_id="s", events=rows)
    assert run.metadata["capture_capabilities"]["source_order"] == "unavailable"


def test_lifecycle_presence_does_not_prove_argument_result_payloads() -> None:
    rows = lifecycle(1, "Read", {})
    rows[0].payload.pop("tool_input")
    rows[1].payload.pop("tool_response")
    run = ClaudeCodeTraceConverter().convert(session_id="s", events=rows)
    assert run.metadata["capture_capabilities"]["action_payloads"] == "unavailable"


def test_event_envelope_is_not_presented_as_tool_arguments() -> None:
    event = build_hook_event(
        {
            "session_id": "s",
            "event_id": "e",
            "tool_use_id": "c",
            "phase": "tool_result",
            "tool_name": "Read",
        }
    )
    assert normalize_hook_event(event).action_evidence.arguments == {}
