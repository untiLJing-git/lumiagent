import pytest
from pydantic import ValidationError

from lumiagent.adapters.mcp import McpFailureType
from lumiagent.adapters.mcp.schemas import (
    McpFailureEvidence,
    McpResultConsumptionEvidence,
    McpToolCallInput,
    McpToolExecutionSummary,
    McpToolSchemaSnapshot,
    McpToolSelectionEvidence,
)


def test_tool_schema_snapshot_accepts_tool_definitions() -> None:
    snapshot = McpToolSchemaSnapshot(
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        schema_version="1",
        tools=[
            {
                "name": "read_file",
                "description": "Read a file",
                "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
            }
        ],
    )

    assert snapshot.server_name == "filesystem"
    assert snapshot.tools[0]["name"] == "read_file"


def test_tool_schema_snapshot_requires_tools() -> None:
    with pytest.raises(ValidationError):
        McpToolSchemaSnapshot(
            server_name="filesystem",
            captured_at="2026-05-26T00:00:00Z",
            schema_version="1",
            tools=[],
        )


def test_tool_call_input_records_arguments_and_validation() -> None:
    call_input = McpToolCallInput(
        server_name="filesystem",
        tool_name="read_file",
        schema_artifact_id="artifact_schema",
        arguments={"path": "src/lumiagent/tracing/models.py"},
        validation={"status": "valid", "errors": []},
    )

    assert call_input.validation["status"] == "valid"


def test_tool_selection_evidence_records_explicit_selection() -> None:
    evidence = McpToolSelectionEvidence(
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file", "list_directory"],
        selection_strategy="explicit",
        reason="Tool name was provided by CLI.",
    )
    assert evidence.selected_tool_name == "read_file"
    assert evidence.available_tool_names == ["read_file", "list_directory"]


def test_execution_summary_records_failure_type() -> None:
    summary = McpToolExecutionSummary(
        status="error",
        latency_ms=1200,
        result_artifact_id=None,
        failure_type=McpFailureType.TIMEOUT,
    )

    assert summary.failure_type is McpFailureType.TIMEOUT


def test_failure_evidence_records_argument_invalid_fields() -> None:
    evidence = McpFailureEvidence(
        failure_type=McpFailureType.ARGUMENT_INVALID,
        failure_stage="argument_generation",
        server_name="filesystem",
        tool_name="read_file",
        schema_artifact_id="artifact_schema",
        call_span_id="span_call",
        validation_errors=[{"path": ["path"], "message": "Field required"}],
    )

    assert evidence.failure_type is McpFailureType.ARGUMENT_INVALID
    assert evidence.validation_errors[0]["message"] == "Field required"


def test_failure_evidence_records_raw_runtime_error_fields() -> None:
    evidence = McpFailureEvidence(
        failure_type=McpFailureType.TOOL_NOT_FOUND,
        failure_stage="tool_selection",
        raw_error_code="tool_not_found",
        raw_error_message="Tool read_me was not found.",
        raw_error_data={"available_tools": ["read_file"]},
        runtime_stage="tool_selection",
    )
    assert evidence.raw_error_code == "tool_not_found"
    assert evidence.raw_error_data == {"available_tools": ["read_file"]}
    assert evidence.runtime_stage == "tool_selection"


def test_result_consumption_evidence_records_misinterpretation_fields() -> None:
    evidence = McpResultConsumptionEvidence(
        consumed_artifact_ids=["artifact_result"],
        consumption_summary="Agent claimed no matching files were returned.",
        claimed_facts=["No matching files were found."],
        contradicted_fields=["content.files[0].path"],
        ignored_key_fields=["content.files"],
        confidence=0.95,
        notes="The result contained a matching source file.",
    )

    assert evidence.contradicted_fields == ["content.files[0].path"]


# --- Validation tests ---


def test_execution_summary_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        McpToolExecutionSummary(status="pending", latency_ms=100)


def test_execution_summary_rejects_negative_latency() -> None:
    with pytest.raises(ValidationError):
        McpToolExecutionSummary(status="success", latency_ms=-1)


def test_failure_evidence_rejects_negative_latency() -> None:
    with pytest.raises(ValidationError):
        McpFailureEvidence(
            failure_type=McpFailureType.TIMEOUT,
            failure_stage="execution",
            latency_ms=-5,
        )


def test_call_input_rejects_whitespace_only_server_name() -> None:
    with pytest.raises(ValidationError):
        McpToolCallInput(server_name="   ", tool_name="read_file")


def test_call_input_rejects_whitespace_only_tool_name() -> None:
    with pytest.raises(ValidationError):
        McpToolCallInput(server_name="filesystem", tool_name="  \t ")


def test_consumption_evidence_rejects_whitespace_only_summary() -> None:
    with pytest.raises(ValidationError):
        McpResultConsumptionEvidence(
            consumed_artifact_ids=["artifact_result"],
            consumption_summary="  ",
        )


def test_consumption_evidence_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        McpResultConsumptionEvidence(
            consumed_artifact_ids=["artifact_result"],
            consumption_summary="Used result",
            confidence=1.5,
        )


def test_consumption_evidence_rejects_confidence_below_zero() -> None:
    with pytest.raises(ValidationError):
        McpResultConsumptionEvidence(
            consumed_artifact_ids=["artifact_result"],
            consumption_summary="Used result",
            confidence=-0.1,
        )
