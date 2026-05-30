from typing import Any

CODING_DOMAIN = "coding_agent"

CODING_USER_PROMPT = "user_prompt"
CODING_TASK_UNDERSTANDING = "task_understanding"
CODING_CONTEXT_GATHERING = "context_gathering"
CODING_FILE_SEARCH = "file_search"
CODING_FILE_READ = "file_read"
CODING_CODE_EDIT = "code_edit"
CODING_SHELL_COMMAND = "shell_command"
CODING_TEST_RUN = "test_run"
CODING_VERIFICATION = "verification"
CODING_GIT_DIFF = "git_diff"
CODING_ERROR_OBSERVED = "error_observed"
CODING_FAILURE_RECOVERY = "failure_recovery"
CODING_RESULT_INTERPRETATION = "result_interpretation"
CODING_PERMISSION_REQUEST = "permission_request"
CODING_APPROVAL_DECISION = "approval_decision"
CODING_FINAL_RESPONSE = "final_response"
CODING_WORKFLOW_CHECK = "workflow_check"

CODING_CONVENTIONS = {
    CODING_USER_PROMPT,
    CODING_TASK_UNDERSTANDING,
    CODING_CONTEXT_GATHERING,
    CODING_FILE_SEARCH,
    CODING_FILE_READ,
    CODING_CODE_EDIT,
    CODING_SHELL_COMMAND,
    CODING_TEST_RUN,
    CODING_VERIFICATION,
    CODING_GIT_DIFF,
    CODING_ERROR_OBSERVED,
    CODING_FAILURE_RECOVERY,
    CODING_RESULT_INTERPRETATION,
    CODING_PERMISSION_REQUEST,
    CODING_APPROVAL_DECISION,
    CODING_FINAL_RESPONSE,
    CODING_WORKFLOW_CHECK,
}

CODING_ARTIFACT_ACTION_EVIDENCE = "coding_action_evidence"
CODING_ARTIFACT_SEMANTIC_EVIDENCE = "coding_semantic_evidence"
CODING_ARTIFACT_WORKFLOW_FINDING = "coding_workflow_finding"
CODING_ARTIFACT_WORKFLOW_CHECKS = "coding_workflow_checks"


def coding_metadata(
    convention: str,
    *,
    source: str,
    source_ids: list[str] | None = None,
    evidence_types: list[str] | None = None,
    classification_reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "domain": CODING_DOMAIN,
        "type": convention,
        "source": source,
    }

    if source_ids is not None:
        metadata["source_event_ids"] = source_ids
    if evidence_types is not None:
        metadata["evidence_types"] = evidence_types
    if classification_reason is not None:
        metadata["classification"] = {
            "strategy": "rule",
            "reason": classification_reason,
        }
    if extra is not None:
        metadata.update(extra)

    return metadata
