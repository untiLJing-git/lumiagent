# MCP Tool Chain Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2 MCP adapter evidence layer without changing the generic Trace Core.

**Architecture:** Add `src/lumiagent/adapters/mcp/` as a convention/helper layer over `lumiagent.tracing`. MCP semantics are represented through centralized `metadata.type` constants, lightweight Pydantic schemas, `McpFailureType`, and helper functions that construct standard `Span`, `Artifact`, `input`, `output`, and evidence payloads using `TraceBuilder`.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, ruff, mypy, existing LumiAgent Trace Core.

---

## File Structure

Create:

- `src/lumiagent/adapters/__init__.py` — marks adapter package.
- `src/lumiagent/adapters/mcp/__init__.py` — public exports for MCP adapter helpers, constants, schemas, and taxonomy.
- `src/lumiagent/adapters/mcp/conventions.py` — centralized span `metadata.type` and artifact `metadata.type` constants.
- `src/lumiagent/adapters/mcp/taxonomy.py` — `McpFailureType` enum outside Core.
- `src/lumiagent/adapters/mcp/schemas.py` — lightweight Pydantic schemas for MCP artifact/evidence payloads.
- `src/lumiagent/adapters/mcp/builder.py` — helper functions around `TraceBuilder`.
- `tests/adapters/mcp/test_taxonomy.py` — enum stability tests.
- `tests/adapters/mcp/test_schemas.py` — schema validation tests.
- `tests/adapters/mcp/test_builder.py` — helper shape and validation tests.
- `tests/adapters/mcp/test_fixtures.py` — fixture serialization and `AgentRun` compatibility tests.
- `tests/adapters/mcp/fixtures/mcp_success_trace.json`
- `tests/adapters/mcp/fixtures/mcp_argument_invalid_trace.json`
- `tests/adapters/mcp/fixtures/mcp_tool_execution_failed_trace.json`
- `tests/adapters/mcp/fixtures/mcp_result_misinterpreted_trace.json`
- `docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md` — Chinese implementation report after code is complete.

Modify:

- `src/lumiagent/__init__.py` only if needed to expose adapter package. If absent or empty, do not create broad exports.

Do not modify:

- `src/lumiagent/tracing/models.py`
- `src/lumiagent/tracing/enums.py`
- `src/lumiagent/tracing/validator.py`

---

### Task 1: Add MCP constants and taxonomy

**Files:**
- Create: `src/lumiagent/adapters/__init__.py`
- Create: `src/lumiagent/adapters/mcp/__init__.py`
- Create: `src/lumiagent/adapters/mcp/conventions.py`
- Create: `src/lumiagent/adapters/mcp/taxonomy.py`
- Test: `tests/adapters/mcp/test_taxonomy.py`

- [ ] **Step 1: Write failing taxonomy tests**

Create `tests/adapters/mcp/test_taxonomy.py`:

```python
from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_ARGUMENT_GENERATION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_PERMISSION,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_mcp_failure_type_values_are_stable() -> None:
    assert [item.value for item in McpFailureType] == [
        "connection_failed",
        "discovery_failed",
        "tool_not_found",
        "schema_unavailable",
        "schema_mismatch",
        "tool_selection_wrong",
        "argument_generation_failed",
        "argument_invalid",
        "permission_required",
        "permission_denied",
        "tool_execution_failed",
        "tool_timeout",
        "tool_result_invalid",
        "result_misinterpreted",
        "insufficient_recovery_evidence",
    ]


def test_mcp_convention_values_are_stable() -> None:
    assert MCP_SPAN_TOOL_CHAIN == "mcp_tool_chain"
    assert MCP_SPAN_CONNECTION == "mcp_connection"
    assert MCP_SPAN_DISCOVERY == "mcp_discovery"
    assert MCP_SPAN_TOOL_SELECTION == "mcp_tool_selection"
    assert MCP_SPAN_ARGUMENT_GENERATION == "mcp_argument_generation"
    assert MCP_SPAN_PERMISSION == "mcp_permission"
    assert MCP_SPAN_TOOL_EXECUTION == "mcp_tool_execution"
    assert MCP_SPAN_RESULT_CONSUMPTION == "mcp_result_consumption"
    assert MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT == "mcp_tool_schema_snapshot"
    assert MCP_ARTIFACT_TOOL_RESULT == "mcp_tool_result"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_taxonomy.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'lumiagent.adapters'` or missing constants.

- [ ] **Step 3: Add adapter package files**

Create `src/lumiagent/adapters/__init__.py`:

```python
"""Adapter packages for framework- and protocol-specific trace conventions."""
```

Create `src/lumiagent/adapters/mcp/conventions.py`:

```python
"""MCP trace convention constants."""
from __future__ import annotations

MCP_SPAN_TOOL_CHAIN = "mcp_tool_chain"
MCP_SPAN_CONNECTION = "mcp_connection"
MCP_SPAN_DISCOVERY = "mcp_discovery"
MCP_SPAN_TOOL_SELECTION = "mcp_tool_selection"
MCP_SPAN_ARGUMENT_GENERATION = "mcp_argument_generation"
MCP_SPAN_PERMISSION = "mcp_permission"
MCP_SPAN_TOOL_EXECUTION = "mcp_tool_execution"
MCP_SPAN_RESULT_CONSUMPTION = "mcp_result_consumption"

MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT = "mcp_tool_schema_snapshot"
MCP_ARTIFACT_TOOL_RESULT = "mcp_tool_result"
```

Create `src/lumiagent/adapters/mcp/taxonomy.py`:

```python
"""MCP failure taxonomy."""
from __future__ import annotations

from enum import StrEnum


class McpFailureType(StrEnum):
    CONNECTION_FAILED = "connection_failed"
    DISCOVERY_FAILED = "discovery_failed"
    TOOL_NOT_FOUND = "tool_not_found"
    SCHEMA_UNAVAILABLE = "schema_unavailable"
    SCHEMA_MISMATCH = "schema_mismatch"
    TOOL_SELECTION_WRONG = "tool_selection_wrong"
    ARGUMENT_GENERATION_FAILED = "argument_generation_failed"
    ARGUMENT_INVALID = "argument_invalid"
    PERMISSION_REQUIRED = "permission_required"
    PERMISSION_DENIED = "permission_denied"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_RESULT_INVALID = "tool_result_invalid"
    RESULT_MISINTERPRETED = "result_misinterpreted"
    INSUFFICIENT_RECOVERY_EVIDENCE = "insufficient_recovery_evidence"
```

Create `src/lumiagent/adapters/mcp/__init__.py`:

```python
"""MCP adapter conventions for LumiAgent traces."""
from .conventions import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_ARGUMENT_GENERATION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_PERMISSION,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from .taxonomy import McpFailureType

__all__ = [
    "MCP_ARTIFACT_TOOL_RESULT",
    "MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT",
    "MCP_SPAN_ARGUMENT_GENERATION",
    "MCP_SPAN_CONNECTION",
    "MCP_SPAN_DISCOVERY",
    "MCP_SPAN_PERMISSION",
    "MCP_SPAN_RESULT_CONSUMPTION",
    "MCP_SPAN_TOOL_CHAIN",
    "MCP_SPAN_TOOL_EXECUTION",
    "MCP_SPAN_TOOL_SELECTION",
    "McpFailureType",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_taxonomy.py -v
```

Expected: PASS.

---

### Task 2: Add lightweight MCP schemas

**Files:**
- Create: `src/lumiagent/adapters/mcp/schemas.py`
- Modify: `src/lumiagent/adapters/mcp/__init__.py`
- Test: `tests/adapters/mcp/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/adapters/mcp/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from lumiagent.adapters.mcp import McpFailureType
from lumiagent.adapters.mcp.schemas import (
    McpFailureEvidence,
    McpResultConsumptionEvidence,
    McpToolCallInput,
    McpToolExecutionSummary,
    McpToolSchemaSnapshot,
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


def test_execution_summary_records_failure_type() -> None:
    summary = McpToolExecutionSummary(
        status="error",
        latency_ms=1200,
        result_artifact_id=None,
        failure_type=McpFailureType.TOOL_TIMEOUT,
    )

    assert summary.failure_type is McpFailureType.TOOL_TIMEOUT


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_schemas.py -v
```

Expected: FAIL because `schemas.py` does not exist.

- [ ] **Step 3: Implement schemas**

Create `src/lumiagent/adapters/mcp/schemas.py`:

```python
"""Lightweight schemas for MCP trace artifacts and evidence."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .taxonomy import McpFailureType


class McpToolSchemaSnapshot(BaseModel):
    server_name: str
    captured_at: str
    schema_version: str | None = None
    tools: list[dict[str, Any]]

    @field_validator("server_name", "captured_at")
    @classmethod
    def require_non_empty_string(cls, value: str) -> str:
        if not value:
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
        if not value:
            raise ValueError("value must not be empty")
        return value


class McpToolExecutionSummary(BaseModel):
    status: str
    latency_ms: int | None = None
    result_artifact_id: str | None = None
    failure_type: McpFailureType | None = None

    @field_validator("status")
    @classmethod
    def require_known_status(cls, value: str) -> str:
        if value not in {"success", "error"}:
            raise ValueError("status must be success or error")
        return value


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
    latency_ms: int | None = None
    permission_status: str | None = None
    consumed_artifact_ids: list[str] = Field(default_factory=list)
    contradicted_fields: list[str] = Field(default_factory=list)
    ignored_key_fields: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("failure_stage")
    @classmethod
    def require_failure_stage(cls, value: str) -> str:
        if not value:
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
        if not value:
            raise ValueError("consumption_summary must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value
```

- [ ] **Step 4: Export schemas**

Update `src/lumiagent/adapters/mcp/__init__.py` to:

```python
"""MCP adapter conventions for LumiAgent traces."""
from .conventions import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_ARGUMENT_GENERATION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_PERMISSION,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from .schemas import (
    McpFailureEvidence,
    McpResultConsumptionEvidence,
    McpToolCallInput,
    McpToolExecutionSummary,
    McpToolSchemaSnapshot,
)
from .taxonomy import McpFailureType

__all__ = [
    "MCP_ARTIFACT_TOOL_RESULT",
    "MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT",
    "MCP_SPAN_ARGUMENT_GENERATION",
    "MCP_SPAN_CONNECTION",
    "MCP_SPAN_DISCOVERY",
    "MCP_SPAN_PERMISSION",
    "MCP_SPAN_RESULT_CONSUMPTION",
    "MCP_SPAN_TOOL_CHAIN",
    "MCP_SPAN_TOOL_EXECUTION",
    "MCP_SPAN_TOOL_SELECTION",
    "McpFailureEvidence",
    "McpFailureType",
    "McpResultConsumptionEvidence",
    "McpToolCallInput",
    "McpToolExecutionSummary",
    "McpToolSchemaSnapshot",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_schemas.py -v
```

Expected: PASS.

---

### Task 3: Add MCP builder helpers

**Files:**
- Create: `src/lumiagent/adapters/mcp/builder.py`
- Modify: `src/lumiagent/adapters/mcp/__init__.py`
- Test: `tests/adapters/mcp/test_builder.py`

- [ ] **Step 1: Write failing builder tests**

Create `tests/adapters/mcp/test_builder.py`:

```python
from lumiagent.adapters.mcp import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    McpFailureType,
)
from lumiagent.adapters.mcp.builder import (
    add_mcp_failure_evidence,
    add_mcp_result_consumption,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    start_mcp_tool_chain,
)
from lumiagent.tracing import ArtifactKind, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.validator import validate_run


def test_mcp_helpers_create_valid_success_trace() -> None:
    builder = TraceBuilder(run_id="run_mcp_success", name="MCP success")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    schema_id = add_mcp_tool_schema_snapshot(
        builder,
        chain_id,
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        tools=[{"name": "read_file", "input_schema": {"type": "object"}}],
    )
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "README.md"},
        schema_artifact_id=schema_id,
        validation={"status": "valid", "errors": []},
    )
    result_id = add_mcp_tool_result(
        builder,
        execution_id,
        content={"text": "# LumiAgent"},
        latency_ms=25,
    )
    add_mcp_result_consumption(
        builder,
        chain_id,
        consumed_artifact_ids=[result_id],
        consumption_summary="Agent read the README heading.",
        claimed_facts=["README starts with LumiAgent."],
    )
    builder.end_span(execution_id, status=SpanStatus.SUCCESS, output={"status": "success"})
    builder.end_span(chain_id, status=SpanStatus.SUCCESS)
    run = builder.build(status=RunStatus.SUCCESS)

    validate_run(run)
    chain = run.root_spans[0]
    execution = chain.children[1]
    consumption = chain.children[2]
    assert chain.kind is SpanKind.CUSTOM
    assert chain.metadata["type"] == MCP_SPAN_TOOL_CHAIN
    assert chain.children[0].metadata["type"] == MCP_SPAN_DISCOVERY
    assert execution.kind is SpanKind.TOOL
    assert execution.metadata["type"] == MCP_SPAN_TOOL_EXECUTION
    assert execution.input["schema_artifact_id"] == schema_id
    assert execution.artifacts[0].kind is ArtifactKind.TOOL_RESULT
    assert execution.artifacts[0].metadata["type"] == MCP_ARTIFACT_TOOL_RESULT
    assert consumption.metadata["type"] == MCP_SPAN_RESULT_CONSUMPTION


def test_mcp_failure_evidence_adds_error_event() -> None:
    builder = TraceBuilder(run_id="run_mcp_failure", name="MCP failure")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={},
        validation={"status": "invalid", "errors": [{"message": "path is required"}]},
    )
    event_id = add_mcp_failure_evidence(
        builder,
        execution_id,
        failure_type=McpFailureType.ARGUMENT_INVALID,
        failure_stage="argument_generation",
        server_name="filesystem",
        tool_name="read_file",
        call_span_id=execution_id,
        validation_errors=[{"message": "path is required"}],
    )
    builder.end_span(execution_id, status=SpanStatus.ERROR, output={"status": "error"})
    builder.end_span(chain_id, status=SpanStatus.ERROR)
    run = builder.build(status=RunStatus.ERROR)

    validate_run(run)
    event = run.root_spans[0].children[0].events[0]
    assert event.event_id == event_id
    assert event.name == "mcp_failure_evidence"
    assert event.metadata["failure_type"] == "argument_invalid"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_builder.py -v
```

Expected: FAIL because `builder.py` helpers do not exist.

- [ ] **Step 3: Implement builder helpers**

Create `src/lumiagent/adapters/mcp/builder.py`:

```python
"""TraceBuilder helpers for MCP tool-chain evidence."""
from __future__ import annotations

from typing import Any

from lumiagent.tracing import ArtifactKind, EventLevel, SpanKind, SpanStatus
from lumiagent.tracing.builder import TraceBuilder

from .conventions import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
)
from .schemas import (
    McpFailureEvidence,
    McpResultConsumptionEvidence,
    McpToolCallInput,
    McpToolExecutionSummary,
    McpToolSchemaSnapshot,
)
from .taxonomy import McpFailureType


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError("value must be a Pydantic model or dictionary")


def start_mcp_tool_chain(
    builder: TraceBuilder,
    *,
    server_name: str,
    parent_span_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    merged_metadata = {"type": MCP_SPAN_TOOL_CHAIN, "server_name": server_name}
    if metadata is not None:
        merged_metadata.update(metadata)
    return builder.start_span(
        "MCP Tool Chain",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        metadata=merged_metadata,
    )


def add_mcp_tool_schema_snapshot(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    server_name: str,
    captured_at: str,
    tools: list[dict[str, Any]],
    schema_version: str | None = None,
) -> str:
    discovery_id = builder.start_span(
        "MCP Tool Discovery",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        metadata={"type": MCP_SPAN_DISCOVERY, "server_name": server_name},
    )
    snapshot = McpToolSchemaSnapshot(
        server_name=server_name,
        captured_at=captured_at,
        schema_version=schema_version,
        tools=tools,
    )
    artifact_id = builder.add_artifact(
        discovery_id,
        name="MCP tool schema snapshot",
        kind=ArtifactKind.CUSTOM,
        content=snapshot.model_dump(mode="json"),
        metadata={"type": MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT, "server_name": server_name},
    )
    builder.end_span(discovery_id, status=SpanStatus.SUCCESS, output={"tool_count": len(tools)})
    return artifact_id


def add_mcp_tool_execution(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    schema_artifact_id: str | None = None,
    validation: dict[str, Any] | None = None,
) -> str:
    call_input = McpToolCallInput(
        server_name=server_name,
        tool_name=tool_name,
        schema_artifact_id=schema_artifact_id,
        arguments=arguments,
        validation=validation or {},
    )
    return builder.start_span(
        f"MCP Tool Execution: {tool_name}",
        kind=SpanKind.TOOL,
        parent_span_id=parent_span_id,
        input_value=call_input.model_dump(mode="json"),
        metadata={"type": MCP_SPAN_TOOL_EXECUTION, "server_name": server_name, "tool_name": tool_name},
    )


def add_mcp_tool_result(
    builder: TraceBuilder,
    execution_span_id: str,
    *,
    content: Any,
    latency_ms: int | None = None,
) -> str:
    artifact_id = builder.add_artifact(
        execution_span_id,
        name="MCP tool result",
        kind=ArtifactKind.TOOL_RESULT,
        content=content,
        metadata={"type": MCP_ARTIFACT_TOOL_RESULT},
    )
    summary = McpToolExecutionSummary(
        status="success",
        latency_ms=latency_ms,
        result_artifact_id=artifact_id,
    )
    builder.add_event(
        execution_span_id,
        name="mcp_tool_result_recorded",
        level=EventLevel.INFO,
        metadata=summary.model_dump(mode="json"),
    )
    return artifact_id


def add_mcp_failure_evidence(
    builder: TraceBuilder,
    span_id: str,
    *,
    failure_type: McpFailureType,
    failure_stage: str,
    server_name: str | None = None,
    tool_name: str | None = None,
    schema_artifact_id: str | None = None,
    call_span_id: str | None = None,
    result_artifact_id: str | None = None,
    evidence_span_ids: list[str] | None = None,
    expected: Any = None,
    actual: Any = None,
    validation_errors: list[dict[str, Any]] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
    permission_status: str | None = None,
    consumed_artifact_ids: list[str] | None = None,
    contradicted_fields: list[str] | None = None,
    ignored_key_fields: list[str] | None = None,
    notes: str = "",
) -> str:
    evidence = McpFailureEvidence(
        failure_type=failure_type,
        failure_stage=failure_stage,
        server_name=server_name,
        tool_name=tool_name,
        schema_artifact_id=schema_artifact_id,
        call_span_id=call_span_id,
        result_artifact_id=result_artifact_id,
        evidence_span_ids=evidence_span_ids or [],
        expected=expected,
        actual=actual,
        validation_errors=validation_errors or [],
        error_code=error_code,
        error_message=error_message,
        latency_ms=latency_ms,
        permission_status=permission_status,
        consumed_artifact_ids=consumed_artifact_ids or [],
        contradicted_fields=contradicted_fields or [],
        ignored_key_fields=ignored_key_fields or [],
        notes=notes,
    )
    return builder.add_event(
        span_id,
        name="mcp_failure_evidence",
        level=EventLevel.ERROR,
        metadata=evidence.model_dump(mode="json"),
    )


def add_mcp_result_consumption(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    consumed_artifact_ids: list[str],
    consumption_summary: str,
    claimed_facts: list[str] | None = None,
    contradicted_fields: list[str] | None = None,
    ignored_key_fields: list[str] | None = None,
    confidence: float | None = None,
    notes: str = "",
) -> str:
    evidence = McpResultConsumptionEvidence(
        consumed_artifact_ids=consumed_artifact_ids,
        consumption_summary=consumption_summary,
        claimed_facts=claimed_facts or [],
        contradicted_fields=contradicted_fields or [],
        ignored_key_fields=ignored_key_fields or [],
        confidence=confidence,
        notes=notes,
    )
    return builder.start_span(
        "MCP Result Consumption",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        metadata={"type": MCP_SPAN_RESULT_CONSUMPTION},
        input_value=evidence.model_dump(mode="json"),
    )
```

- [ ] **Step 4: Export builder helpers**

Append builder imports and names to `src/lumiagent/adapters/mcp/__init__.py`:

```python
from .builder import (
    add_mcp_failure_evidence,
    add_mcp_result_consumption,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    start_mcp_tool_chain,
)
```

Add these strings to `__all__`:

```python
"add_mcp_failure_evidence",
"add_mcp_result_consumption",
"add_mcp_tool_execution",
"add_mcp_tool_result",
"add_mcp_tool_schema_snapshot",
"start_mcp_tool_chain",
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_builder.py -v
```

Expected: PASS.

---

### Task 4: Add MCP JSON fixtures and fixture tests

**Files:**
- Create: `tests/adapters/mcp/fixtures/mcp_success_trace.json`
- Create: `tests/adapters/mcp/fixtures/mcp_argument_invalid_trace.json`
- Create: `tests/adapters/mcp/fixtures/mcp_tool_execution_failed_trace.json`
- Create: `tests/adapters/mcp/fixtures/mcp_result_misinterpreted_trace.json`
- Create: `tests/adapters/mcp/test_fixtures.py`

- [ ] **Step 1: Write fixture tests**

Create `tests/adapters/mcp/test_fixtures.py`:

```python
from pathlib import Path

from lumiagent.adapters.mcp import (
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_SPAN_RESULT_CONSUMPTION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType
from lumiagent.tracing.serializer import from_json
from lumiagent.tracing.validator import validate_run

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    return from_json((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_success_fixture_validates_and_contains_mcp_chain() -> None:
    run = _load_fixture("mcp_success_trace.json")

    validate_run(run)
    chain = run.root_spans[0]
    execution = chain.children[1]
    assert chain.metadata["type"] == MCP_SPAN_TOOL_CHAIN
    assert execution.metadata["type"] == MCP_SPAN_TOOL_EXECUTION
    assert chain.children[0].artifacts[0].metadata["type"] == MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT
    assert execution.artifacts[0].metadata["type"] == MCP_ARTIFACT_TOOL_RESULT
    assert chain.children[2].metadata["type"] == MCP_SPAN_RESULT_CONSUMPTION


def test_argument_invalid_fixture_contains_required_evidence() -> None:
    run = _load_fixture("mcp_argument_invalid_trace.json")

    validate_run(run)
    event = run.root_spans[0].children[1].events[0]
    assert event.metadata["failure_type"] == McpFailureType.ARGUMENT_INVALID.value
    assert event.metadata["schema_artifact_id"] == "artifact_schema_argument_invalid"
    assert event.metadata["call_span_id"] == "span_argument_invalid_execution"
    assert event.metadata["validation_errors"]


def test_tool_execution_failed_fixture_contains_required_evidence() -> None:
    run = _load_fixture("mcp_tool_execution_failed_trace.json")

    validate_run(run)
    event = run.root_spans[0].children[1].events[0]
    assert event.metadata["failure_type"] == McpFailureType.TOOL_EXECUTION_FAILED.value
    assert event.metadata["call_span_id"] == "span_execution_failed_execution"
    assert event.metadata["error_code"] == "EIO"
    assert event.metadata["latency_ms"] == 350


def test_result_misinterpreted_fixture_contains_required_evidence() -> None:
    run = _load_fixture("mcp_result_misinterpreted_trace.json")

    validate_run(run)
    consumption = run.root_spans[0].children[2]
    event = consumption.events[0]
    assert event.metadata["failure_type"] == McpFailureType.RESULT_MISINTERPRETED.value
    assert event.metadata["result_artifact_id"] == "artifact_result_misinterpreted"
    assert event.metadata["consumed_artifact_ids"] == ["artifact_result_misinterpreted"]
    assert event.metadata["contradicted_fields"] == ["content.files[0].path"]
    assert event.metadata["ignored_key_fields"] == ["content.files"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_fixtures.py -v
```

Expected: FAIL because fixture files do not exist.

- [ ] **Step 3: Create fixtures through a generation script in the shell**

Run this PowerShell command from the repository root:

```powershell
@'
from pathlib import Path

from lumiagent.adapters.mcp import McpFailureType
from lumiagent.adapters.mcp.builder import (
    add_mcp_failure_evidence,
    add_mcp_result_consumption,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    start_mcp_tool_chain,
)
from lumiagent.tracing import RunStatus, SpanStatus
from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.serializer import to_json

fixture_dir = Path("tests/adapters/mcp/fixtures")
fixture_dir.mkdir(parents=True, exist_ok=True)


def write(name, run):
    (fixture_dir / name).write_text(to_json(run), encoding="utf-8")


def success_trace():
    builder = TraceBuilder(run_id="run_mcp_success", name="MCP success trace")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    schema_id = add_mcp_tool_schema_snapshot(
        builder,
        chain_id,
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        tools=[{"name": "read_file", "input_schema": {"type": "object"}}],
    )
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "README.md"},
        schema_artifact_id=schema_id,
        validation={"status": "valid", "errors": []},
    )
    result_id = add_mcp_tool_result(builder, execution_id, content={"text": "# LumiAgent"}, latency_ms=25)
    consumption_id = add_mcp_result_consumption(
        builder,
        chain_id,
        consumed_artifact_ids=[result_id],
        consumption_summary="Agent used the README heading.",
        claimed_facts=["README starts with LumiAgent."],
    )
    builder.end_span(consumption_id, status=SpanStatus.SUCCESS, output={"status": "consumed"})
    builder.end_span(execution_id, status=SpanStatus.SUCCESS, output={"status": "success", "result_artifact_id": result_id})
    builder.end_span(chain_id, status=SpanStatus.SUCCESS)
    return builder.build(status=RunStatus.SUCCESS)


def argument_invalid_trace():
    builder = TraceBuilder(run_id="run_mcp_argument_invalid", name="MCP argument invalid trace")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    schema_id = add_mcp_tool_schema_snapshot(
        builder,
        chain_id,
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        tools=[{"name": "read_file", "input_schema": {"required": ["path"]}}],
    )
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={},
        schema_artifact_id=schema_id,
        validation={"status": "invalid", "errors": [{"message": "path is required"}]},
    )
    builder._get_span(chain_id).children[0].artifacts[0].artifact_id = "artifact_schema_argument_invalid"
    builder._get_span(execution_id).span_id = "span_argument_invalid_execution"
    add_mcp_failure_evidence(
        builder,
        "span_argument_invalid_execution",
        failure_type=McpFailureType.ARGUMENT_INVALID,
        failure_stage="argument_generation",
        server_name="filesystem",
        tool_name="read_file",
        schema_artifact_id="artifact_schema_argument_invalid",
        call_span_id="span_argument_invalid_execution",
        validation_errors=[{"message": "path is required"}],
    )
    builder.end_span("span_argument_invalid_execution", status=SpanStatus.ERROR, output={"status": "error", "failure_type": "argument_invalid"})
    builder.end_span(chain_id, status=SpanStatus.ERROR)
    return builder.build(status=RunStatus.ERROR)


def execution_failed_trace():
    builder = TraceBuilder(run_id="run_mcp_execution_failed", name="MCP execution failed trace")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    schema_id = add_mcp_tool_schema_snapshot(
        builder,
        chain_id,
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        tools=[{"name": "read_file", "input_schema": {"required": ["path"]}}],
    )
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "missing.md"},
        schema_artifact_id=schema_id,
        validation={"status": "valid", "errors": []},
    )
    builder._get_span(execution_id).span_id = "span_execution_failed_execution"
    add_mcp_failure_evidence(
        builder,
        "span_execution_failed_execution",
        failure_type=McpFailureType.TOOL_EXECUTION_FAILED,
        failure_stage="execution",
        server_name="filesystem",
        tool_name="read_file",
        call_span_id="span_execution_failed_execution",
        error_code="EIO",
        error_message="File read failed.",
        latency_ms=350,
    )
    builder.end_span("span_execution_failed_execution", status=SpanStatus.ERROR, output={"status": "error", "failure_type": "tool_execution_failed"})
    builder.end_span(chain_id, status=SpanStatus.ERROR)
    return builder.build(status=RunStatus.ERROR)


def result_misinterpreted_trace():
    builder = TraceBuilder(run_id="run_mcp_result_misinterpreted", name="MCP result misinterpreted trace")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    schema_id = add_mcp_tool_schema_snapshot(
        builder,
        chain_id,
        server_name="filesystem",
        captured_at="2026-05-26T00:00:00Z",
        tools=[{"name": "search_files", "input_schema": {"required": ["query"]}}],
    )
    execution_id = add_mcp_tool_execution(
        builder,
        chain_id,
        server_name="filesystem",
        tool_name="search_files",
        arguments={"query": "TraceBuilder"},
        schema_artifact_id=schema_id,
        validation={"status": "valid", "errors": []},
    )
    result_id = add_mcp_tool_result(
        builder,
        execution_id,
        content={"files": [{"path": "src/lumiagent/tracing/builder.py"}]},
        latency_ms=40,
    )
    builder._get_span(execution_id).artifacts[0].artifact_id = "artifact_result_misinterpreted"
    consumption_id = add_mcp_result_consumption(
        builder,
        chain_id,
        consumed_artifact_ids=["artifact_result_misinterpreted"],
        consumption_summary="Agent claimed no matching files were found.",
        claimed_facts=["No matching files were found."],
        contradicted_fields=["content.files[0].path"],
        ignored_key_fields=["content.files"],
        confidence=0.95,
    )
    add_mcp_failure_evidence(
        builder,
        consumption_id,
        failure_type=McpFailureType.RESULT_MISINTERPRETED,
        failure_stage="result_consumption",
        server_name="filesystem",
        tool_name="search_files",
        result_artifact_id="artifact_result_misinterpreted",
        consumed_artifact_ids=["artifact_result_misinterpreted"],
        contradicted_fields=["content.files[0].path"],
        ignored_key_fields=["content.files"],
    )
    builder.end_span(consumption_id, status=SpanStatus.ERROR, output={"status": "error", "failure_type": "result_misinterpreted"})
    builder.end_span(execution_id, status=SpanStatus.SUCCESS, output={"status": "success", "result_artifact_id": result_id})
    builder.end_span(chain_id, status=SpanStatus.ERROR)
    return builder.build(status=RunStatus.ERROR)

write("mcp_success_trace.json", success_trace())
write("mcp_argument_invalid_trace.json", argument_invalid_trace())
write("mcp_tool_execution_failed_trace.json", execution_failed_trace())
write("mcp_result_misinterpreted_trace.json", result_misinterpreted_trace())
'@ | python
```

Expected: four JSON fixture files are created.

- [ ] **Step 4: Run fixture tests**

Run:

```powershell
python -m pytest tests/adapters/mcp/test_fixtures.py -v
```

Expected: PASS.

---

### Task 5: Add implementation report and run full verification

**Files:**
- Create: `docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md`

- [ ] **Step 1: Write Chinese technical report**

Create `docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md`:

```markdown
# MCP Tool Chain Model 技术报告

## 阶段目标

本阶段建立 MCP Tool Chain Evidence Layer，用于记录 Coding Agent 使用 MCP 工具链时的结构化证据。

## 技术选择

- 继续复用 Trace Core 的 `AgentRun / Span / Event / Artifact`。
- 在 `src/lumiagent/adapters/mcp/` 中新增 MCP adapter/convention 层。
- 使用 `metadata.type` 表达 MCP 语义，避免污染 Core enum。
- 使用 Pydantic v2 定义轻量 evidence schema。

## 设计模式

- Core / Adapter 分离。
- Failure taxonomy 位于 MCP adapter 层。
- Tool schema snapshot 和 tool result 使用 artifact。
- Tool arguments 使用 `mcp_tool_execution.input`。
- Result consumption evidence 使用独立 span 表达。

## 实现亮点

- `McpFailureType` 覆盖连接、发现、schema、选择、参数、权限、执行、结果消费等失败类型。
- Builder helpers 统一生成 MCP spans、artifacts、events 和 evidence metadata。
- Fixtures 覆盖成功链路、调用前失败、执行失败和调用后误读。

## 验证结果

运行以下命令：

```powershell
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

结果：全部通过。

## 风险与取舍

- 本阶段不接真实 MCP SDK，因此 connection/discovery 仍是 trace convention，不是 runtime capture。
- `result_misinterpreted` 只记录局部 MCP result consumption evidence，不判断完整 Coding Agent 任务成败。
- Retry/Fallback/Recovery 暂用通用 span/event 表达，后续可在 workflow recovery 层统一设计。

## 后续建议

- Phase 3 在 Coding Agent Trace 中消费 MCP evidence layer。
- Phase 4 将 `McpFailureType` 映射为 Evaluation / Diagnosis 输出。
- 后续 MCP SDK 接入时，在 `src/lumiagent/adapters/mcp/` 下新增 runtime capture 模块。
```

- [ ] **Step 2: Run full tests**

Run:

```powershell
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Run ruff**

Run:

```powershell
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
```

Expected: `All checks passed!`

- [ ] **Step 4: Run mypy**

Run:

```powershell
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

Expected: `Success: no issues found`.

- [ ] **Step 5: Review git diff**

Run:

```powershell
git diff --stat
```

Expected: diff includes MCP adapter files, MCP tests, fixtures, and Chinese technical report. Core tracing model files should not be modified.

---

## Self-Review

- Spec coverage: The plan covers adapter location, taxonomy, conventions, schemas, helpers, required fixtures, tests, validation, and Chinese technical report.
- Scope check: The plan does not add real MCP SDK integration, UI, runtime proxy, or Core model changes.
- Placeholder scan: No `TBD`, `TODO`, `FIXME`, or unspecified implementation steps remain.
- Type consistency: Function names and schema names are introduced before use and exported through `lumiagent.adapters.mcp`.
