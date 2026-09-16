"""Conservative workflow prechecks, not task evaluation or causal diagnosis."""

from __future__ import annotations

from pydantic import ValidationError

from lumiagent.adapters.coding.events import (
    CaptureCapabilities,
    CodingWorkflowChecks,
    CodingWorkflowFinding,
    WorkflowAggregateStatus,
)
from lumiagent.adapters.coding.ordering import flatten_spans, source_position, source_relation
from lumiagent.tracing import AgentRun, Span, SpanStatus

RULE_VERSION = "coding_workflow.v2"


def _kind(span: Span) -> object:
    return span.metadata.get("type")


def _same_context(a: Span, b: Span) -> bool | None:
    left, right = source_position(a), source_position(b)
    if left is None or right is None:
        return None
    if (left.session_id, left.scope_id) != (right.session_id, right.scope_id):
        return False
    a_cwd, b_cwd = a.metadata.get("working_directory"), b.metadata.get("working_directory")
    return not (a_cwd is not None and b_cwd is not None and a_cwd != b_cwd)


def _related(failed: Span, candidate: Span) -> bool | None:
    refs = candidate.metadata.get("related_span_ids", [])
    if isinstance(refs, list) and failed.span_id in refs:
        return True
    a, b = source_position(failed), source_position(candidate)
    if a is not None and b is not None and (a.session_id, a.scope_id) != (b.session_id, b.scope_id):
        return False
    if failed.metadata.get("call_id") and failed.metadata.get("call_id") == candidate.metadata.get(
        "call_id"
    ):
        return True
    if isinstance(failed.input, dict) and isinstance(candidate.input, dict):
        command = failed.input.get("command")
        if command and candidate.input.get("command"):
            # A different working directory is a different verification target.
            cwd_a, cwd_b = (
                failed.metadata.get("working_directory"),
                candidate.metadata.get("working_directory"),
            )
            if cwd_a is None or cwd_b is None:
                return None
            if cwd_a != cwd_b:
                return False
            if "[REDACTED]" in str(command) or "[REDACTED]" in str(candidate.input["command"]):
                return None
            return bool(command == candidate.input["command"])
    return None


def validate_coding_workflow(run: AgentRun) -> CodingWorkflowChecks:
    try:
        caps = CaptureCapabilities.model_validate(run.metadata.get("capture_capabilities", {}))
    except ValidationError:
        caps = CaptureCapabilities(gaps=["invalid_capture_capabilities"])
    complete = caps.workflow_coverage == "complete"
    spans = [
        s
        for s in flatten_spans(run.root_spans)
        if s.metadata.get("type") not in {"workflow_check", "context_gathering", "coding_agent_run"}
        and not (s.children and s.metadata.get("type") == "verification")
    ]
    findings: list[CodingWorkflowFinding] = []
    applicable = False

    def finding(
        rule: str,
        anchor: Span,
        uncertain: bool,
        summary: str,
        related: list[Span] | None = None,
        *,
        severity: str = "warning",
    ) -> None:
        findings.append(
            CodingWorkflowFinding(
                schema_version="coding_workflow_finding.v2",
                rule_id=rule,
                status="unknown" if uncertain else "failed",
                severity="info" if uncertain else ("error" if severity == "error" else "warning"),
                confidence="low" if uncertain else "high",
                summary=summary,
                evidence_span_ids=[anchor.span_id],
                related_span_ids=[s.span_id for s in related or []],
                expected="A related action with reliable source order and outcome evidence.",
                actual="Insufficient evidence."
                if uncertain
                else "Requirement not met in declared scope.",
            )
        )

    for anchor in spans:
        kind = _kind(anchor)
        if kind == "code_edit" and anchor.status == SpanStatus.SUCCESS:
            applicable = True
            candidates = [
                s
                for s in spans
                if _kind(s) in {"test_run", "verification"}
                and _same_context(anchor, s) is not False
            ]
            satisfied = any(
                source_relation(anchor, s) == "before"
                and _same_context(anchor, s) is True
                and s.status == SpanStatus.SUCCESS
                for s in candidates
            )
            if not satisfied:
                uncertain = not complete or any(
                    source_relation(anchor, s) == "unknown"
                    or _same_context(anchor, s) is None
                    or (
                        source_relation(anchor, s) == "before"
                        and s.status in {SpanStatus.RUNNING, SpanStatus.PENDING, SpanStatus.SKIPPED}
                    )
                    for s in candidates
                )
                finding(
                    "code_edit_requires_verification",
                    anchor,
                    uncertain,
                    "No reliably later successful verification was observed.",
                )
        if kind in {"test_run", "shell_command"} and anchor.status == SpanStatus.ERROR:
            applicable = True
            candidates = [
                s
                for s in spans
                if s is not anchor
                and _kind(s) in {kind, "failure_recovery", "verification"}
                and s.status == SpanStatus.SUCCESS
            ]
            satisfied = any(
                source_relation(anchor, s) == "before" and _related(anchor, s) is True
                for s in candidates
            )
            if not satisfied:
                uncertain = not complete or any(
                    source_relation(anchor, s) in {"before", "unknown"}
                    and _related(anchor, s) is not False
                    for s in candidates
                )
                rule = (
                    "failed_test_requires_recovery"
                    if kind == "test_run"
                    else "failed_command_requires_recovery"
                )
                finding(
                    rule,
                    anchor,
                    uncertain,
                    "No related successful recovery was confirmed.",
                    severity="error" if kind == "test_run" else "warning",
                )
        if kind == "approval_decision" and anchor.status == SpanStatus.ERROR:
            applicable = True
            for candidate in spans:
                if (
                    _kind(candidate) not in {"shell_command", "code_edit"}
                    or candidate.status != SpanStatus.SUCCESS
                ):
                    continue
                relation, related = source_relation(anchor, candidate), _related(anchor, candidate)
                if relation in {"before", "unknown"} and related is not False:
                    finding(
                        "permission_denied_blocks_action",
                        anchor,
                        relation == "unknown" or related is None,
                        "A possibly related action follows a denied approval.",
                        [candidate],
                        severity="error",
                    )
        if kind == "error_observed":
            applicable = True
            finals = [
                s
                for s in spans
                if _kind(s) == "final_response"
                and source_relation(anchor, s) in {"before", "unknown"}
            ]
            for final in finals:
                recovered = any(
                    _kind(s) in {"failure_recovery", "test_run", "verification"}
                    and s.status == SpanStatus.SUCCESS
                    and _related(anchor, s) is True
                    and source_relation(anchor, s) == "before"
                    and source_relation(s, final) == "before"
                    for s in spans
                )
                if not recovered:
                    finding(
                        "final_response_after_unresolved_error",
                        anchor,
                        not complete or source_relation(anchor, final) == "unknown",
                        "Final response without confirmed related recovery.",
                        [final],
                    )
    status: WorkflowAggregateStatus
    if any(f.status == "failed" and f.severity == "error" for f in findings):
        status = "error"
    elif any(f.status == "failed" for f in findings):
        status = "warning"
    elif not complete or any(f.status == "unknown" for f in findings):
        status = "unknown"
    else:
        status = "pass" if applicable else "not_applicable"
    return CodingWorkflowChecks(
        schema_version="coding_workflow_checks.v2",
        rule_version=RULE_VERSION,
        status=status,
        findings=findings,
        limitations=[]
        if complete
        else ["Capture completeness is not established; absence is not failure."],
    )
