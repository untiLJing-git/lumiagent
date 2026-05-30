from lumiagent.adapters.coding.events import (
    CodingActionEvidence,
    CodingSemanticEvidence,
    CodingWorkflowChecks,
    CodingWorkflowFinding,
    NormalizedCodingEvent,
)


def test_action_evidence_defaults_to_raw_redaction() -> None:
    evidence = CodingActionEvidence(
        tool_name="Bash",
        arguments={"command": "python -m pytest -v"},
        result={"status": "success", "exit_code": 0},
    )

    assert evidence.artifact_type == "coding_action_evidence"
    assert evidence.schema_version == "coding_action_evidence.v1"
    assert evidence.safety == {"redaction_state": "raw"}


def test_semantic_evidence_records_summary_and_confidence() -> None:
    evidence = CodingSemanticEvidence(
        convention="task_understanding",
        role="assistant",
        content_summary="Inspect tests and package layout.",
        confidence="medium",
    )

    assert evidence.artifact_type == "coding_semantic_evidence"
    assert evidence.source == "transcript_enrichment"
    assert evidence.content is None


def test_normalized_event_links_source_events_and_evidence() -> None:
    event = NormalizedCodingEvent(
        event_id="coding_evt_1",
        source_event_ids=["evt_1"],
        session_id="session_1",
        sequence=1,
        convention="test_run",
        status="success",
        name="Run pytest",
        action_evidence=CodingActionEvidence(tool_name="Bash"),
        metadata={"classification_reason": "pytest command"},
    )

    assert event.convention == "test_run"
    assert event.action_evidence is not None
    assert event.semantic_evidence is None


def test_workflow_checks_aggregate_status() -> None:
    finding = CodingWorkflowFinding(
        rule_id="code_edit_requires_verification",
        status="failed",
        severity="warning",
        summary="Code was edited without verification.",
        evidence_span_ids=["span_1"],
    )
    checks = CodingWorkflowChecks(status="warning", findings=[finding])

    assert checks.schema_version == "coding_workflow_checks.v1"
    assert checks.findings[0].confidence == "high"
