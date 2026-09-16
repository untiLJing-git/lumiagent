"""Adapter evidence integrity and explicit, non-destructive precheck refresh."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lumiagent.adapters.coding.events import CodingWorkflowChecks, CodingWorkflowFinding
from lumiagent.adapters.coding.ordering import flatten_spans
from lumiagent.tracing import (
    AgentRun,
    Artifact,
    ArtifactKind,
    Span,
    SpanKind,
    SpanStatus,
    TraceValidationError,
    validate_run,
)

AuditStatus = Literal["valid", "invalid", "unknown"]
WORKFLOW_TYPES = {"coding_workflow_checks", "coding_workflow_finding"}


class EvidenceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str | None = None
    code: str
    message: str


class EvidenceAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AuditStatus = "unknown"
    issues: list[EvidenceIssue] = Field(default_factory=list)
    artifact_statuses: dict[str, AuditStatus] = Field(default_factory=dict)


def workflow_subject_digest(run: AgentRun) -> str:
    def strip(span: Span) -> dict[str, Any]:
        value = span.model_dump(mode="json")
        value["children"] = [
            strip(c) for c in span.children if c.metadata.get("type") != "workflow_check"
        ]
        value["artifacts"] = [
            a.model_dump(mode="json")
            for a in span.artifacts
            if a.metadata.get("type") not in WORKFLOW_TYPES
        ]
        return value

    value = {
        "run_id": run.run_id,
        "capture_capabilities": run.metadata.get("capture_capabilities"),
        "root_spans": [
            strip(s) for s in run.root_spans if s.metadata.get("type") != "workflow_check"
        ],
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def audit_coding_evidence(run: AgentRun) -> EvidenceAudit:
    audit = EvidenceAudit()
    try:
        validate_run(run)
    except TraceValidationError as exc:
        return EvidenceAudit(
            status="invalid", issues=[EvidenceIssue(code="invalid_core", message=str(exc))]
        )
    spans = flatten_spans(run.root_spans)
    duplicates = {
        key
        for key, count in Counter(a.artifact_id for s in spans for a in s.artifacts).items()
        if count > 1
    }
    for key in sorted(duplicates):
        audit.issues.append(
            EvidenceIssue(
                artifact_id=key,
                code="duplicate_artifact_id",
                message="Artifact identity is not unique within the run.",
            )
        )
    ids = {span.span_id for span in spans}
    digest = workflow_subject_digest(run)
    for span in spans:
        for artifact in span.artifacts:
            if artifact.metadata.get("type") not in WORKFLOW_TYPES:
                continue
            status: AuditStatus = "valid"
            try:
                if artifact.metadata["type"] == "coding_workflow_checks":
                    checks = CodingWorkflowChecks.model_validate(artifact.content)
                    findings = checks.findings
                    if (
                        checks.schema_version != "coding_workflow_checks.v2"
                        or checks.rule_version != "coding_workflow.v2"
                    ):
                        status = "unknown"
                        audit.issues.append(
                            EvidenceIssue(
                                artifact_id=artifact.artifact_id,
                                code="historical_checks",
                                message="Stored prechecks are not current rule evidence.",
                            )
                        )
                    elif checks.subject_digest != digest:
                        status = "invalid"
                        audit.issues.append(
                            EvidenceIssue(
                                artifact_id=artifact.artifact_id,
                                code="stale_subject",
                                message="Prechecks do not match the current subject.",
                            )
                        )
                else:
                    findings = [CodingWorkflowFinding.model_validate(artifact.content)]
                    status = (
                        "unknown"  # No subject/version binding for a standalone historical finding.
                    )
                if status == "valid" and artifact.metadata["type"] == "coding_workflow_checks":
                    from lumiagent.adapters.coding.validator import validate_coding_workflow

                    expected = validate_coding_workflow(run)
                    if checks.model_dump(exclude={"subject_digest"}) != expected.model_dump(
                        exclude={"subject_digest"}
                    ):
                        status = "invalid"
                        audit.issues.append(
                            EvidenceIssue(
                                artifact_id=artifact.artifact_id,
                                code="inconsistent_checks",
                                message="Stored verdict differs from current prechecks.",
                            )
                        )
                for finding in findings:
                    for ref in finding.evidence_span_ids + finding.related_span_ids:
                        if ref not in ids:
                            status = "invalid"
                            audit.issues.append(
                                EvidenceIssue(
                                    artifact_id=artifact.artifact_id,
                                    code="dangling_span",
                                    message=f"Evidence span {ref} does not exist.",
                                )
                            )
            except ValidationError:
                status = "invalid"
                audit.issues.append(
                    EvidenceIssue(
                        artifact_id=artifact.artifact_id,
                        code="malformed_artifact",
                        message="Workflow evidence does not match its schema.",
                    )
                )
            audit.artifact_statuses[artifact.artifact_id] = status
    statuses = set(audit.artifact_statuses.values())
    audit.status = (
        "invalid"
        if "invalid" in statuses or duplicates
        else ("unknown" if not statuses or "unknown" in statuses else "valid")
    )
    return audit


def append_workflow_checks(run: AgentRun) -> None:
    """Append current checks in place to a newly built run, without regenerating action IDs."""
    from lumiagent.adapters.coding.validator import validate_coding_workflow

    validate_run(run)
    checks = validate_coding_workflow(run)
    checks.subject_digest = workflow_subject_digest(run)
    previous = [
        a.artifact_id
        for s in flatten_spans(run.root_spans)
        for a in s.artifacts
        if a.metadata.get("type") == "coding_workflow_checks"
    ]
    parent = run.root_spans[0] if run.root_spans else None
    check_span = Span(
        run_id=run.run_id,
        parent_span_id=parent.span_id if parent else None,
        name="Workflow Check",
        kind=SpanKind.CUSTOM,
        status=SpanStatus.SKIPPED if checks.status == "unknown" else SpanStatus.SUCCESS,
        metadata={
            "domain": "coding_agent",
            "type": "workflow_check",
            "source": "workflow_validator",
            "timestamp_basis": "ingestion",
        },
        artifacts=[
            Artifact(
                name="Workflow Checks",
                kind=ArtifactKind.JSON,
                content=checks.model_dump(mode="json"),
                metadata={"type": "coding_workflow_checks", "supersedes_artifact_ids": previous},
            )
        ],
    )
    check_span.ended_at = check_span.started_at
    if parent is None:
        run.root_spans.append(check_span)
    else:
        parent.children.append(check_span)
    validate_run(run)


def refresh_workflow_checks(run: AgentRun) -> AgentRun:
    """Keep original artifacts verbatim; append a versioned replacement on a copy."""
    copy = run.model_copy(deep=True)
    append_workflow_checks(copy)
    return copy
