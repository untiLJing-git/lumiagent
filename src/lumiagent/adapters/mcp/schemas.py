"""Lightweight schemas for MCP trace artifacts and evidence."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .taxonomy import McpFailureType  # noqa: TC001


class McpToolSchemaSnapshot(BaseModel):
    server_name: str
    captured_at: str
    schema_version: str | None = None
    tools: list[dict[str, Any]]

    @field_validator("server_name", "captured_at")
    @classmethod
    def require_non_empty_string(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("tools")
    @classmethod
    def require_tools(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise ValueError("tools must not be empty")
        return value


class McpToolCallInput(BaseModel):
    server_name: str
    tool_name: str
    schema_artifact_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)

    @field_validator("server_name", "tool_name")
    @classmethod
    def require_non_empty_string(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class McpToolSelectionEvidence(BaseModel):
    requested_tool_name: str
    selected_tool_name: str | None = None
    available_tool_names: list[str] = Field(default_factory=list)
    selection_strategy: str = "explicit"
    reason: str = ""

    @field_validator("requested_tool_name", "selection_strategy")
    @classmethod
    def require_non_empty_string(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

class McpToolExecutionSummary(BaseModel):
    status: Literal["success", "error"]
    latency_ms: int | None = Field(default=None, ge=0)
    result_artifact_id: str | None = None
    failure_type: McpFailureType | None = None


class McpFailureEvidence(BaseModel):
    failure_type: McpFailureType
    failure_stage: str
    server_name: str | None = None
    tool_name: str | None = None
    schema_artifact_id: str | None = None
    call_span_id: str | None = None
    result_artifact_id: str | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)
    expected: Any = None
    actual: Any = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    raw_error_code: str | None = None
    raw_error_message: str | None = None
    raw_error_data: dict[str, Any] | None = None
    runtime_stage: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    permission_status: str | None = None
    consumed_artifact_ids: list[str] = Field(default_factory=list)
    contradicted_fields: list[str] = Field(default_factory=list)
    ignored_key_fields: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("failure_stage")
    @classmethod
    def require_failure_stage(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("failure_stage must not be empty")
        return value


class McpResultConsumptionEvidence(BaseModel):
    consumed_artifact_ids: list[str]
    consumption_summary: str
    claimed_facts: list[str] = Field(default_factory=list)
    contradicted_fields: list[str] = Field(default_factory=list)
    ignored_key_fields: list[str] = Field(default_factory=list)
    confidence: float | None = None
    notes: str = ""

    @field_validator("consumed_artifact_ids")
    @classmethod
    def require_consumed_artifacts(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("consumed_artifact_ids must not be empty")
        return value

    @field_validator("consumption_summary")
    @classmethod
    def require_consumption_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("consumption_summary must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value
