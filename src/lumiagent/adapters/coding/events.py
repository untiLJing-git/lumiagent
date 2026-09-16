"""Normalized Coding Agent event and evidence schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_ARTIFACT_WORKFLOW_FINDING,
)

CodingStatus = Literal["success", "error", "running", "unknown"]
WorkflowAggregateStatus = Literal["pass", "warning", "error", "not_applicable", "unknown"]
WorkflowFindingStatus = Literal["passed", "failed", "not_applicable", "unknown"]
WorkflowSeverity = Literal["info", "warning", "error"]
Confidence = Literal["high", "medium", "low"]


class CodingActionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = CODING_ARTIFACT_ACTION_EVIDENCE
    schema_version: str = "coding_action_evidence.v1"
    source: str = "claude_code_hook"
    tool_name: str | None = None
    server_name: str | None = None
    schema_status: Literal["unavailable", "unverified"] = "unavailable"
    raw_result: Any = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=lambda: {"redaction_state": "raw"})


class CodingSemanticEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = CODING_ARTIFACT_SEMANTIC_EVIDENCE
    schema_version: str = "coding_semantic_evidence.v1"
    source: str = "transcript_enrichment"
    convention: str
    role: str
    content_summary: str
    content: str | None = None
    confidence: Confidence = "medium"
    safety: dict[str, Any] = Field(default_factory=lambda: {"redaction_state": "raw"})


class NormalizedCodingEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    source_event_ids: list[str] = Field(default_factory=list)
    session_id: str
    sequence: int
    timestamp: str | None = None
    convention: str
    status: CodingStatus = "unknown"
    parent_convention: str | None = None
    name: str
    action_evidence: CodingActionEvidence | None = None
    semantic_evidence: CodingSemanticEvidence | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodingWorkflowFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = CODING_ARTIFACT_WORKFLOW_FINDING
    schema_version: str = "coding_workflow_finding.v1"
    rule_id: str
    status: WorkflowFindingStatus
    severity: WorkflowSeverity
    summary: str
    evidence_span_ids: list[str] = Field(default_factory=list)
    related_span_ids: list[str] = Field(default_factory=list)
    expected: str = ""
    actual: str = ""
    confidence: Confidence = "high"


class CodingWorkflowChecks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = CODING_ARTIFACT_WORKFLOW_CHECKS
    schema_version: str = "coding_workflow_checks.v1"
    status: WorkflowAggregateStatus
    findings: list[CodingWorkflowFinding] = Field(default_factory=list)
    rule_version: str | None = None
    subject_digest: str | None = None
    limitations: list[str] = Field(default_factory=list)


Availability = Literal["available", "partial", "unavailable", "unknown"]


class CaptureCapabilities(BaseModel):
    """Declared coverage and measured availability; never infer completeness from success."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["coding_capture_capabilities.v1"] = "coding_capture_capabilities.v1"
    workflow_coverage: Literal["complete", "partial", "unknown"] = "unknown"
    coverage_basis: str | None = None
    source_identity: Availability = "unknown"
    call_identity: Availability = "unknown"
    source_order: Availability = "unknown"
    source_time: Availability = "unknown"
    action_payloads: Availability = "unknown"
    mcp_schema: Availability = "unavailable"
    task_input: Availability = "unknown"
    final_response: Availability = "unknown"
    final_state: Availability = "unknown"
    model_configuration: Availability = "unknown"
    resource_usage: Availability = "unknown"
    costs: Availability = "unknown"
    gaps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_coverage_basis(self) -> CaptureCapabilities:
        if self.workflow_coverage == "complete" and not (self.coverage_basis or "").strip():
            raise ValueError("complete coverage requires an explicit coverage_basis")
        return self
