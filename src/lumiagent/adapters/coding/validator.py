"""Deterministic Coding Agent workflow checks."""
from __future__ import annotations

from lumiagent.adapters.coding.conventions import (
    CODING_APPROVAL_DECISION,
    CODING_CODE_EDIT,
    CODING_ERROR_OBSERVED,
    CODING_FAILURE_RECOVERY,
    CODING_FINAL_RESPONSE,
    CODING_SHELL_COMMAND,
    CODING_TEST_RUN,
    CODING_VERIFICATION,
)
from lumiagent.adapters.coding.events import (
    CodingWorkflowChecks,
    CodingWorkflowFinding,
    WorkflowAggregateStatus,
)
from lumiagent.tracing import AgentRun, Span, SpanStatus


def validate_coding_workflow(run: AgentRun) -> CodingWorkflowChecks:
    spans = _flatten(run.root_spans)
    findings: list[CodingWorkflowFinding] = []
    findings.extend(_check_code_edit_requires_verification(spans))
    findings.extend(_check_failed_test_requires_recovery(spans))
    findings.extend(_check_failed_command_requires_recovery(spans))
    findings.extend(_check_permission_denied_blocks_action(spans))
    findings.extend(_check_final_response_after_unresolved_error(spans))
    return CodingWorkflowChecks(status=_aggregate(findings), findings=findings)


def _check_code_edit_requires_verification(spans: list[Span]) -> list[CodingWorkflowFinding]:
    edits = [span for span in spans if span.metadata.get("type") == CODING_CODE_EDIT]
    if not edits:
        return []
    last_edit_index = max(spans.index(span) for span in edits)
    later_types = {span.metadata.get("type") for span in spans[last_edit_index + 1 :]}
    if CODING_TEST_RUN in later_types or CODING_VERIFICATION in later_types:
        return []
    return [
        CodingWorkflowFinding(
            rule_id="code_edit_requires_verification",
            status="failed",
            severity="warning",
            summary="Code was edited without a later test or verification span.",
            evidence_span_ids=[span.span_id for span in edits],
            expected="A code_edit span should be followed by test_run or verification.",
            actual="No later test_run or verification span was found.",
        )
    ]


def _check_failed_test_requires_recovery(spans: list[Span]) -> list[CodingWorkflowFinding]:
    findings: list[CodingWorkflowFinding] = []
    for index, span in enumerate(spans):
        if span.metadata.get("type") != CODING_TEST_RUN or span.status != SpanStatus.ERROR:
            continue
        later = spans[index + 1 :]
        recovered = any(
            item.metadata.get("type") in {CODING_FAILURE_RECOVERY, CODING_CODE_EDIT}
            or (item.metadata.get("type") == CODING_TEST_RUN and item.status == SpanStatus.SUCCESS)
            for item in later
        )
        if not recovered:
            findings.append(
                CodingWorkflowFinding(
                    rule_id="failed_test_requires_recovery",
                    status="failed",
                    severity="error",
                    summary="A failed test run was not followed by recovery.",
                    evidence_span_ids=[span.span_id],
                    expected=(
                        "A failed test_run should be followed by recovery or a passing test_run."
                    ),
                    actual="No later recovery action or passing test_run was found.",
                )
            )
    return findings


def _check_failed_command_requires_recovery(spans: list[Span]) -> list[CodingWorkflowFinding]:
    findings: list[CodingWorkflowFinding] = []
    for index, span in enumerate(spans):
        if span.metadata.get("type") != CODING_SHELL_COMMAND or span.status != SpanStatus.ERROR:
            continue
        if _has_later_type(
            spans,
            index,
            {CODING_FAILURE_RECOVERY, CODING_CODE_EDIT, CODING_TEST_RUN, CODING_VERIFICATION},
        ):
            continue
        findings.append(
            CodingWorkflowFinding(
                rule_id="failed_command_requires_recovery",
                status="failed",
                severity="warning",
                summary="A failed shell command was not followed by recovery.",
                evidence_span_ids=[span.span_id],
                expected="A failed shell_command should be followed by recovery or verification.",
                actual="No later recovery or verification span was found.",
            )
        )
    return findings


def _check_permission_denied_blocks_action(spans: list[Span]) -> list[CodingWorkflowFinding]:
    findings: list[CodingWorkflowFinding] = []
    for index, span in enumerate(spans):
        if span.metadata.get("type") != CODING_APPROVAL_DECISION or span.status != SpanStatus.ERROR:
            continue
        later_risky = [
            item
            for item in spans[index + 1 :]
            if item.metadata.get("type") in {CODING_SHELL_COMMAND, CODING_CODE_EDIT}
        ]
        if later_risky:
            findings.append(
                CodingWorkflowFinding(
                    rule_id="permission_denied_blocks_action",
                    status="failed",
                    severity="error",
                    summary="A denied approval was followed by a risky action.",
                    evidence_span_ids=[span.span_id],
                    related_span_ids=[item.span_id for item in later_risky],
                    expected="A denied approval should block related risky actions.",
                    actual="A later risky action span was found after denial.",
                )
            )
    return findings


def _check_final_response_after_unresolved_error(spans: list[Span]) -> list[CodingWorkflowFinding]:
    findings: list[CodingWorkflowFinding] = []
    for index, span in enumerate(spans):
        if span.metadata.get("type") != CODING_ERROR_OBSERVED:
            continue
        later = spans[index + 1 :]
        has_recovery = any(
            item.metadata.get("type")
            in {CODING_FAILURE_RECOVERY, CODING_TEST_RUN, CODING_VERIFICATION}
            for item in later
        )
        final_spans = [item for item in later if item.metadata.get("type") == CODING_FINAL_RESPONSE]
        if final_spans and not has_recovery:
            findings.append(
                CodingWorkflowFinding(
                    rule_id="final_response_after_unresolved_error",
                    status="failed",
                    severity="warning",
                    summary="A final response followed an unresolved error.",
                    evidence_span_ids=[span.span_id],
                    related_span_ids=[item.span_id for item in final_spans],
                    expected=(
                        "An observed error should be recovered or verified before final response."
                    ),
                    actual="Final response appeared without recovery or verification.",
                )
            )
    return findings


def _has_later_type(spans: list[Span], index: int, span_types: set[str]) -> bool:
    return any(span.metadata.get("type") in span_types for span in spans[index + 1 :])


def _aggregate(findings: list[CodingWorkflowFinding]) -> WorkflowAggregateStatus:
    if any(finding.severity == "error" for finding in findings):
        return "error"
    if any(finding.severity == "warning" for finding in findings):
        return "warning"
    return "pass"


def _flatten(spans: list[Span]) -> list[Span]:
    flattened: list[Span] = []
    for span in spans:
        flattened.append(span)
        flattened.extend(_flatten(span.children))
    return flattened
