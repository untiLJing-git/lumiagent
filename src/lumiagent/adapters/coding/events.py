"""Normalized Coding Agent event and evidence schemas."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_ARTIFACT_WORKFLOW_FINDING,
)

CodingStatus = Literal["success", "error", "running", "unknown"]
WorkflowAggregateStatus = Literal["pass", "warning", "error", "not_applicable"]
WorkflowFindingStatus = Literal["passed", "failed", "not_applicable"]
WorkflowSeverity = Literal["info", "warning", "error"]
Confidence = Literal["high", "medium", "low"]


class CodingActionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = CODING_ARTIFACT_ACTION_EVIDENCE
    schema_version: str = "coding_action_evidence.v1"
    source: str = "claude_code_hook"
    tool_name: str | None = None
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
