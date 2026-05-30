from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_CODE_EDIT,
    CODING_CONTEXT_GATHERING,
    CODING_CONVENTIONS,
    CODING_DOMAIN,
    CODING_FINAL_RESPONSE,
    CODING_TEST_RUN,
    coding_metadata,
)


def test_coding_conventions_are_stable() -> None:
    assert CODING_DOMAIN == "coding_agent"
    assert CODING_CONTEXT_GATHERING == "context_gathering"
    assert CODING_CODE_EDIT == "code_edit"
    assert CODING_TEST_RUN == "test_run"
    assert CODING_FINAL_RESPONSE == "final_response"
    assert CODING_ARTIFACT_ACTION_EVIDENCE == "coding_action_evidence"
    assert CODING_ARTIFACT_SEMANTIC_EVIDENCE == "coding_semantic_evidence"
    assert CODING_ARTIFACT_WORKFLOW_CHECKS == "coding_workflow_checks"
    assert {
        "user_prompt",
        "task_understanding",
        "context_gathering",
        "file_search",
        "file_read",
        "code_edit",
        "shell_command",
        "test_run",
        "verification",
        "git_diff",
        "error_observed",
        "failure_recovery",
        "result_interpretation",
        "permission_request",
        "approval_decision",
        "final_response",
        "workflow_check",
    } == CODING_CONVENTIONS


def test_coding_metadata_records_domain_type_and_evidence() -> None:
    metadata = coding_metadata(
        "test_run",
        source="claude_code_hook",
        source_ids=["evt_1", "evt_2"],
        evidence_types=["action_evidence"],
        classification_reason="pytest command",
    )

    assert metadata == {
        "domain": "coding_agent",
        "type": "test_run",
        "source": "claude_code_hook",
        "source_event_ids": ["evt_1", "evt_2"],
        "evidence_types": ["action_evidence"],
        "classification": {"strategy": "rule", "reason": "pytest command"},
    }
