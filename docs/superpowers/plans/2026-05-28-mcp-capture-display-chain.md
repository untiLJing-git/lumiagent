# MCP Capture + Display Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 2b so LumiAgent can capture a real third-party stdio MCP server interaction, convert success/failure into valid `AgentRun` traces, and display MCP evidence in the CLI.

**Architecture:** Add a generic `CaptureStrategy` protocol, then keep MCP capture in `src/lumiagent/adapters/mcp/` behind transport-agnostic runtime, explicit tool selection, trace mapping, capture orchestration, and viewer modules. The first concrete runtime supports stdio only, but `McpCaptureStrategy` depends on the runtime protocol so HTTP/SSE can be added later without changing mapping or CLI display.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, pytest, ruff, mypy, existing Trace Core and MCP adapter helpers, optional third-party MCP SDK for stdio runtime if available in dependencies.

---

## File Structure

Create these files:

- `src/lumiagent/capture/__init__.py` — public export for generic capture interfaces.
- `src/lumiagent/capture/strategy.py` — `CaptureStrategy` protocol.
- `src/lumiagent/adapters/mcp/runtime.py` — transport-agnostic runtime protocol, runtime data models, stdio runtime implementation, and runtime error type.
- `src/lumiagent/adapters/mcp/selector.py` — explicit tool selector and selection result/evidence models.
- `src/lumiagent/adapters/mcp/mapper.py` — maps runtime/selection results into Trace Core `AgentRun` using MCP conventions.
- `src/lumiagent/adapters/mcp/capture.py` — `McpCaptureConfig` and `McpCaptureStrategy` orchestration.
- `src/lumiagent/adapters/mcp/viewer.py` — readable MCP trace summary lines for `lumiagent show`.
- `tests/capture/test_strategy.py` — generic capture protocol importability.
- `tests/adapters/mcp/test_runtime.py` — runtime model and stdio construction tests.
- `tests/adapters/mcp/test_selector.py` — explicit tool selection tests.
- `tests/adapters/mcp/test_mapper.py` — success/failure trace mapping tests.
- `tests/adapters/mcp/test_capture.py` — strategy orchestration tests with fake runtime.
- `tests/adapters/mcp/test_viewer.py` — CLI viewer summary tests.
- `tests/test_cli_mcp.py` — Typer command parser tests for capture/show.
- `docs/reports/mcp-capture-display-chain-technical-report.zh-CN.md` — Chinese technical report after implementation.

Modify these files:

- `src/lumiagent/adapters/mcp/taxonomy.py` — align failure taxonomy with Phase 2b spec while preserving existing values.
- `src/lumiagent/adapters/mcp/conventions.py` — add missing initialization and selection/result artifact convention constants.
- `src/lumiagent/adapters/mcp/schemas.py` — add tool selection schema and raw runtime error fields to failure evidence.
- `src/lumiagent/adapters/mcp/builder.py` — add helper for initialization span and tool selection span/artifact; keep existing helpers compatible.
- `src/lumiagent/adapters/mcp/__init__.py` — export new adapter APIs.
- `src/lumiagent/cli.py` — add `capture mcp` and `show` commands.
- `README.md` and `README.zh-CN.md` — update project structure/status only after implementation and verification.

Do not modify `src/lumiagent/tracing/` for MCP-specific semantics.

---

### Task 1: Generic CaptureStrategy Protocol

**Files:**
- Create: `src/lumiagent/capture/__init__.py`
- Create: `src/lumiagent/capture/strategy.py`
- Test: `tests/capture/test_strategy.py`

- [ ] **Step 1: Write the failing protocol import test**

Create `tests/capture/test_strategy.py`:

```python
from lumiagent.capture import CaptureStrategy


def test_capture_strategy_protocol_is_public() -> None:
    assert CaptureStrategy.__name__ == "CaptureStrategy"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/capture/test_strategy.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'lumiagent.capture'`.

- [ ] **Step 3: Implement the protocol**

Create `src/lumiagent/capture/strategy.py`:

```python
"""Generic capture strategy protocol."""
from __future__ import annotations

from typing import Protocol

from lumiagent.tracing import AgentRun


class CaptureStrategy(Protocol):
    def capture(self) -> AgentRun: ...
```

Create `src/lumiagent/capture/__init__.py`:

```python
"""Capture strategy public API."""
from lumiagent.capture.strategy import CaptureStrategy

__all__ = ["CaptureStrategy"]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/capture/test_strategy.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/capture/__init__.py" "src/lumiagent/capture/strategy.py" "tests/capture/test_strategy.py"
git commit -m @'
Add capture strategy protocol
'@
```

---

### Task 2: Expand MCP Taxonomy and Conventions

**Files:**
- Modify: `src/lumiagent/adapters/mcp/taxonomy.py`
- Modify: `src/lumiagent/adapters/mcp/conventions.py`
- Test: `tests/adapters/mcp/test_taxonomy.py`

- [ ] **Step 1: Replace taxonomy test with Phase 2b stable values**

Modify `tests/adapters/mcp/test_taxonomy.py` so it contains:

```python
from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_FAILURE_EVIDENCE,
    MCP_ARTIFACT_TOOL_RESULT,
    MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT,
    MCP_ARTIFACT_TOOL_SELECTION,
    MCP_SPAN_CONNECTION,
    MCP_SPAN_DISCOVERY,
    MCP_SPAN_INITIALIZATION,
    MCP_SPAN_TOOL_CHAIN,
    MCP_SPAN_TOOL_EXECUTION,
    MCP_SPAN_TOOL_SELECTION,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_mcp_failure_type_values_are_stable() -> None:
    assert [item.value for item in McpFailureType] == [
        "connection_failed",
        "initialization_failed",
        "tool_discovery_failed",
        "tool_not_found",
        "argument_invalid",
        "permission_denied",
        "tool_execution_failed",
        "timeout",
        "transport_interrupted",
        "result_invalid",
        "result_misinterpreted",
        "unknown",
    ]


def test_existing_mcp_failure_values_remain_available() -> None:
    assert McpFailureType.ARGUMENT_INVALID.value == "argument_invalid"
    assert McpFailureType.TOOL_EXECUTION_FAILED.value == "tool_execution_failed"
    assert McpFailureType.RESULT_MISINTERPRETED.value == "result_misinterpreted"


def test_mcp_convention_values_are_stable() -> None:
    assert MCP_SPAN_TOOL_CHAIN == "mcp_tool_chain"
    assert MCP_SPAN_CONNECTION == "mcp_connection"
    assert MCP_SPAN_INITIALIZATION == "mcp_initialization"
    assert MCP_SPAN_DISCOVERY == "mcp_discovery"
    assert MCP_SPAN_TOOL_SELECTION == "mcp_tool_selection"
    assert MCP_SPAN_TOOL_EXECUTION == "mcp_tool_execution"
    assert MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT == "mcp_tool_schema_snapshot"
    assert MCP_ARTIFACT_TOOL_SELECTION == "mcp_tool_selection"
    assert MCP_ARTIFACT_TOOL_RESULT == "mcp_tool_result"
    assert MCP_ARTIFACT_FAILURE_EVIDENCE == "mcp_failure_evidence"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_taxonomy.py -v
```

Expected: FAIL because `INITIALIZATION_FAILED`, `TOOL_DISCOVERY_FAILED`, `TIMEOUT`, `TRANSPORT_INTERRUPTED`, `RESULT_INVALID`, `UNKNOWN`, `MCP_SPAN_INITIALIZATION`, `MCP_ARTIFACT_TOOL_SELECTION`, or `MCP_ARTIFACT_FAILURE_EVIDENCE` do not exist.

- [ ] **Step 3: Update taxonomy and convention constants**

Replace `src/lumiagent/adapters/mcp/taxonomy.py` with:

```python
"""MCP failure taxonomy."""

from __future__ import annotations

from enum import StrEnum


class McpFailureType(StrEnum):
    CONNECTION_FAILED = "connection_failed"
    INITIALIZATION_FAILED = "initialization_failed"
    TOOL_DISCOVERY_FAILED = "tool_discovery_failed"
    TOOL_NOT_FOUND = "tool_not_found"
    ARGUMENT_INVALID = "argument_invalid"
    PERMISSION_DENIED = "permission_denied"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TIMEOUT = "timeout"
    TRANSPORT_INTERRUPTED = "transport_interrupted"
    RESULT_INVALID = "result_invalid"
    RESULT_MISINTERPRETED = "result_misinterpreted"
    UNKNOWN = "unknown"
```

Replace `src/lumiagent/adapters/mcp/conventions.py` with:

```python
"""MCP trace convention constants."""

MCP_SPAN_TOOL_CHAIN = "mcp_tool_chain"
MCP_SPAN_CONNECTION = "mcp_connection"
MCP_SPAN_INITIALIZATION = "mcp_initialization"
MCP_SPAN_DISCOVERY = "mcp_discovery"
MCP_SPAN_TOOL_SELECTION = "mcp_tool_selection"
MCP_SPAN_ARGUMENT_GENERATION = "mcp_argument_generation"
MCP_SPAN_PERMISSION = "mcp_permission"
MCP_SPAN_TOOL_EXECUTION = "mcp_tool_execution"
MCP_SPAN_RESULT_CONSUMPTION = "mcp_result_consumption"

MCP_ARTIFACT_TOOL_SCHEMA_SNAPSHOT = "mcp_tool_schema_snapshot"
MCP_ARTIFACT_TOOL_SELECTION = "mcp_tool_selection"
MCP_ARTIFACT_TOOL_RESULT = "mcp_tool_result"
MCP_ARTIFACT_FAILURE_EVIDENCE = "mcp_failure_evidence"
```

- [ ] **Step 4: Run taxonomy tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_taxonomy.py -v
```

Expected: PASS.

- [ ] **Step 5: Run existing MCP tests to catch compatibility breaks**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp -v
```

Expected: Some existing fixture/schema tests may fail because old failure names such as `discovery_failed`, `tool_timeout`, or `tool_result_invalid` were removed. Update fixtures or schema tests only if they reference removed names; keep `argument_invalid`, `tool_execution_failed`, and `result_misinterpreted` unchanged.

- [ ] **Step 6: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/taxonomy.py" "src/lumiagent/adapters/mcp/conventions.py" "tests/adapters/mcp/test_taxonomy.py" "tests/adapters/mcp"
git commit -m @'
Expand MCP failure taxonomy
'@
```

---

### Task 3: MCP Runtime Models and Protocol

**Files:**
- Create: `src/lumiagent/adapters/mcp/runtime.py`
- Test: `tests/adapters/mcp/test_runtime.py`

- [ ] **Step 1: Write failing runtime model tests**

Create `tests/adapters/mcp/test_runtime.py`:

```python
import pytest
from pydantic import ValidationError

from lumiagent.adapters.mcp.runtime import (
    McpConnectionInfo,
    McpClientRuntime,
    McpRuntimeError,
    McpRuntimeStage,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
    StdioMcpClientRuntime,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_runtime_protocol_is_public() -> None:
    assert McpClientRuntime.__name__ == "McpClientRuntime"


def test_runtime_data_models_capture_transport_and_tool_result() -> None:
    connection = McpConnectionInfo(
        transport="stdio",
        server_name="filesystem",
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "."],
    )
    session = McpSessionInfo(protocol_version="2024-11-05", server_name="filesystem")
    tool = McpToolDefinition(
        name="read_file",
        description="Read a file",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
    )
    result = McpToolCallResult(
        tool_name="read_file",
        arguments={"path": "README.md"},
        content=[{"type": "text", "text": "# LumiAgent"}],
        is_error=False,
        latency_ms=12,
    )

    assert connection.transport == "stdio"
    assert session.server_name == "filesystem"
    assert tool.name == "read_file"
    assert result.content[0]["type"] == "text"


def test_runtime_error_carries_failure_type_and_stage() -> None:
    error = McpRuntimeError(
        failure_type=McpFailureType.TOOL_NOT_FOUND,
        stage=McpRuntimeStage.TOOL_SELECTION,
        message="Tool read_me was not found.",
        raw_error_code="tool_not_found",
        raw_error_data={"available_tools": ["read_file"]},
    )

    assert error.failure_type is McpFailureType.TOOL_NOT_FOUND
    assert error.stage is McpRuntimeStage.TOOL_SELECTION
    assert error.raw_error_data == {"available_tools": ["read_file"]}


def test_tool_definition_requires_name() -> None:
    with pytest.raises(ValidationError):
        McpToolDefinition(name="", input_schema={})


def test_stdio_runtime_stores_launch_configuration() -> None:
    runtime = StdioMcpClientRuntime(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        server_name="filesystem",
        timeout_seconds=5,
    )

    assert runtime.server_command == "npx"
    assert runtime.server_args == ["-y", "@modelcontextprotocol/server-filesystem", "."]
    assert runtime.server_name == "filesystem"
    assert runtime.timeout_seconds == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_runtime.py -v
```

Expected: FAIL because `runtime.py` does not exist.

- [ ] **Step 3: Implement runtime models and protocol shell**

Create `src/lumiagent/adapters/mcp/runtime.py`:

```python
"""Transport-agnostic MCP client runtime interfaces."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator

from lumiagent.adapters.mcp.taxonomy import McpFailureType


class McpRuntimeStage(StrEnum):
    CONNECTION = "connection"
    INITIALIZATION = "initialization"
    TOOL_DISCOVERY = "tool_discovery"
    TOOL_SELECTION = "tool_selection"
    TOOL_EXECUTION = "tool_execution"
    RESULT_PARSING = "result_parsing"


class McpConnectionInfo(BaseModel):
    transport: str
    server_name: str
    server_command: str | None = None
    server_args: list[str] = Field(default_factory=list)

    @field_validator("transport", "server_name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class McpSessionInfo(BaseModel):
    protocol_version: str | None = None
    server_name: str | None = None
    capabilities: dict[str, Any] = Field(default_factory=dict)


class McpToolDefinition(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool name must not be empty")
        return value


class McpToolCallResult(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    content: list[Any] = Field(default_factory=list)
    is_error: bool = False
    latency_ms: int | None = Field(default=None, ge=0)
    raw_result: Any = None

    @field_validator("tool_name")
    @classmethod
    def require_tool_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool_name must not be empty")
        return value


class McpRuntimeError(Exception):
    def __init__(
        self,
        *,
        failure_type: McpFailureType,
        stage: McpRuntimeStage,
        message: str,
        raw_error_code: str | None = None,
        raw_error_data: Any = None,
    ) -> None:
        super().__init__(message)
        self.failure_type = failure_type
        self.stage = stage
        self.message = message
        self.raw_error_code = raw_error_code
        self.raw_error_data = raw_error_data


class McpClientRuntime(Protocol):
    def connect(self) -> McpConnectionInfo: ...

    def initialize(self) -> McpSessionInfo: ...

    def list_tools(self) -> list[McpToolDefinition]: ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult: ...

    def close(self) -> None: ...


class StdioMcpClientRuntime:
    def __init__(
        self,
        *,
        server_command: str,
        server_args: list[str] | None = None,
        server_name: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.server_command = server_command
        self.server_args = server_args or []
        self.server_name = server_name or server_command
        self.timeout_seconds = timeout_seconds

    def connect(self) -> McpConnectionInfo:
        raise NotImplementedError("Stdio MCP connection is implemented in Task 9")

    def initialize(self) -> McpSessionInfo:
        raise NotImplementedError("Stdio MCP initialization is implemented in Task 9")

    def list_tools(self) -> list[McpToolDefinition]:
        raise NotImplementedError("Stdio MCP tool discovery is implemented in Task 9")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult:
        raise NotImplementedError("Stdio MCP tool execution is implemented in Task 9")

    def close(self) -> None:
        return None
```

- [ ] **Step 4: Run runtime tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_runtime.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/runtime.py" "tests/adapters/mcp/test_runtime.py"
git commit -m @'
Add MCP runtime protocol models
'@
```

---

### Task 4: Explicit Tool Selector

**Files:**
- Create: `src/lumiagent/adapters/mcp/selector.py`
- Test: `tests/adapters/mcp/test_selector.py`

- [ ] **Step 1: Write failing selector tests**

Create `tests/adapters/mcp/test_selector.py`:

```python
import pytest

from lumiagent.adapters.mcp.runtime import McpToolDefinition
from lumiagent.adapters.mcp.selector import ExplicitToolSelector, McpToolSelection
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_explicit_tool_selector_selects_requested_tool() -> None:
    selector = ExplicitToolSelector()
    selection = selector.select(
        requested_tool_name="read_file",
        tools=[
            McpToolDefinition(name="list_directory"),
            McpToolDefinition(name="read_file", input_schema={"type": "object"}),
        ],
    )

    assert isinstance(selection, McpToolSelection)
    assert selection.requested_tool_name == "read_file"
    assert selection.selected_tool_name == "read_file"
    assert selection.available_tool_names == ["list_directory", "read_file"]
    assert selection.selection_strategy == "explicit"


def test_explicit_tool_selector_raises_tool_not_found() -> None:
    selector = ExplicitToolSelector()

    with pytest.raises(ValueError) as exc_info:
        selector.select(
            requested_tool_name="read_me",
            tools=[McpToolDefinition(name="read_file")],
        )

    assert "tool_not_found" in str(exc_info.value)


def test_tool_selection_serializes_as_evidence() -> None:
    selection = McpToolSelection(
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file"],
        reason="Tool name was provided by CLI.",
    )

    assert selection.model_dump(mode="json") == {
        "requested_tool_name": "read_file",
        "selected_tool_name": "read_file",
        "available_tool_names": ["read_file"],
        "selection_strategy": "explicit",
        "reason": "Tool name was provided by CLI.",
    }


def test_selector_failure_type_constant_is_tool_not_found() -> None:
    assert McpFailureType.TOOL_NOT_FOUND.value == "tool_not_found"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_selector.py -v
```

Expected: FAIL because `selector.py` does not exist.

- [ ] **Step 3: Implement selector**

Create `src/lumiagent/adapters/mcp/selector.py`:

```python
"""MCP tool selection helpers."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from lumiagent.adapters.mcp.runtime import McpToolDefinition
from lumiagent.adapters.mcp.taxonomy import McpFailureType


class McpToolSelection(BaseModel):
    requested_tool_name: str
    selected_tool_name: str
    available_tool_names: list[str] = Field(default_factory=list)
    selection_strategy: str = "explicit"
    reason: str = "Tool name was provided by CLI."

    @field_validator("requested_tool_name", "selected_tool_name", "selection_strategy", "reason")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class ExplicitToolSelector:
    def select(
        self,
        *,
        requested_tool_name: str,
        tools: list[McpToolDefinition],
    ) -> McpToolSelection:
        available_tool_names = [tool.name for tool in tools]
        if requested_tool_name not in available_tool_names:
            raise ValueError(
                f"{McpFailureType.TOOL_NOT_FOUND.value}: requested tool "
                f"{requested_tool_name!r} is not available"
            )
        return McpToolSelection(
            requested_tool_name=requested_tool_name,
            selected_tool_name=requested_tool_name,
            available_tool_names=available_tool_names,
        )
```

- [ ] **Step 4: Run selector tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_selector.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/selector.py" "tests/adapters/mcp/test_selector.py"
git commit -m @'
Add explicit MCP tool selector
'@
```

---

### Task 5: MCP Schemas and Builder Helpers for Selection/Initialization

**Files:**
- Modify: `src/lumiagent/adapters/mcp/schemas.py`
- Modify: `src/lumiagent/adapters/mcp/builder.py`
- Test: `tests/adapters/mcp/test_schemas.py`
- Test: `tests/adapters/mcp/test_mcp_builder.py`

- [ ] **Step 1: Add failing schema tests**

Append to `tests/adapters/mcp/test_schemas.py`:

```python
from lumiagent.adapters.mcp.schemas import McpToolSelectionEvidence


def test_tool_selection_evidence_records_explicit_selection() -> None:
    evidence = McpToolSelectionEvidence(
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file", "list_directory"],
        selection_strategy="explicit",
        reason="Tool name was provided by CLI.",
    )

    assert evidence.selected_tool_name == "read_file"
    assert evidence.available_tool_names == ["read_file", "list_directory"]


def test_failure_evidence_records_raw_runtime_error_fields() -> None:
    evidence = McpFailureEvidence(
        failure_type=McpFailureType.TOOL_NOT_FOUND,
        failure_stage="tool_selection",
        raw_error_code="tool_not_found",
        raw_error_message="Tool read_me was not found.",
        raw_error_data={"available_tools": ["read_file"]},
        runtime_stage="tool_selection",
    )

    assert evidence.raw_error_code == "tool_not_found"
    assert evidence.raw_error_data == {"available_tools": ["read_file"]}
    assert evidence.runtime_stage == "tool_selection"
```

- [ ] **Step 2: Add failing builder tests**

Append to `tests/adapters/mcp/test_mcp_builder.py`:

```python
from lumiagent.adapters.mcp.conventions import (
    MCP_ARTIFACT_TOOL_SELECTION,
    MCP_SPAN_INITIALIZATION,
    MCP_SPAN_TOOL_SELECTION,
)
from lumiagent.adapters.mcp.builder import add_mcp_initialization, add_mcp_tool_selection


def test_mcp_builder_records_initialization_and_tool_selection() -> None:
    builder = TraceBuilder(run_id="run_selection", name="selection demo")
    chain_id = start_mcp_tool_chain(builder, server_name="filesystem")
    init_id = add_mcp_initialization(
        builder,
        chain_id,
        server_name="filesystem",
        protocol_version="2024-11-05",
        capabilities={"tools": True},
    )
    selection_id = add_mcp_tool_selection(
        builder,
        chain_id,
        server_name="filesystem",
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file"],
        reason="Tool name was provided by CLI.",
    )
    builder.end_span(chain_id)
    run = builder.build()

    validate_run(run)
    assert run.root_spans[0].children[0].metadata["type"] == MCP_SPAN_INITIALIZATION
    assert run.root_spans[0].children[1].metadata["type"] == MCP_SPAN_TOOL_SELECTION
    assert run.root_spans[0].children[1].artifacts[0].metadata["type"] == MCP_ARTIFACT_TOOL_SELECTION
    assert init_id != selection_id
```

If imports duplicate existing imports, merge them instead of adding second import blocks.

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_schemas.py tests/adapters/mcp/test_mcp_builder.py -v
```

Expected: FAIL because `McpToolSelectionEvidence`, raw runtime fields, `add_mcp_initialization`, and `add_mcp_tool_selection` do not exist.

- [ ] **Step 4: Implement schema additions**

Add to `src/lumiagent/adapters/mcp/schemas.py` after `McpToolCallInput`:

```python
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
```

Add fields to `McpFailureEvidence`:

```python
    raw_error_code: str | None = None
    raw_error_message: str | None = None
    raw_error_data: Any = None
    runtime_stage: str | None = None
```

- [ ] **Step 5: Implement builder helpers**

Update imports in `src/lumiagent/adapters/mcp/builder.py` to include `MCP_SPAN_INITIALIZATION`, `MCP_SPAN_TOOL_SELECTION`, `MCP_ARTIFACT_TOOL_SELECTION`, `McpToolSelectionEvidence`, and `ArtifactKind` already present.

Add after `start_mcp_tool_chain`:

```python
def add_mcp_initialization(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    server_name: str,
    protocol_version: str | None = None,
    capabilities: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    initialization_id = builder.start_span(
        "MCP Initialization",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        metadata=_merge_metadata(
            {"type": MCP_SPAN_INITIALIZATION, "server_name": server_name}, metadata
        ),
    )
    builder.end_span(
        initialization_id,
        status=SpanStatus.SUCCESS,
        output={
            "protocol_version": protocol_version,
            "capabilities": capabilities or {},
        },
    )
    return initialization_id


def add_mcp_tool_selection(
    builder: TraceBuilder,
    parent_span_id: str,
    *,
    server_name: str,
    requested_tool_name: str,
    selected_tool_name: str | None = None,
    available_tool_names: list[str] | None = None,
    selection_strategy: str = "explicit",
    reason: str = "",
    status: SpanStatus = SpanStatus.SUCCESS,
    metadata: dict[str, Any] | None = None,
) -> str:
    evidence = McpToolSelectionEvidence(
        requested_tool_name=requested_tool_name,
        selected_tool_name=selected_tool_name,
        available_tool_names=available_tool_names or [],
        selection_strategy=selection_strategy,
        reason=reason,
    )
    selection_id = builder.start_span(
        f"MCP Tool Selection: {requested_tool_name}",
        kind=SpanKind.CUSTOM,
        parent_span_id=parent_span_id,
        input_value=evidence.model_dump(mode="json"),
        metadata=_merge_metadata(
            {
                "type": MCP_SPAN_TOOL_SELECTION,
                "server_name": server_name,
                "requested_tool_name": requested_tool_name,
                "selected_tool_name": selected_tool_name,
            },
            metadata,
        ),
    )
    builder.add_artifact(
        selection_id,
        name="MCP Tool Selection",
        kind=ArtifactKind.CUSTOM,
        content=evidence.model_dump(mode="json"),
        metadata={"type": MCP_ARTIFACT_TOOL_SELECTION, "server_name": server_name},
    )
    builder.end_span(selection_id, status=status, output=evidence.model_dump(mode="json"))
    return selection_id
```

Extend `add_mcp_failure_evidence` signature and `McpFailureEvidence` construction with:

```python
    raw_error_code: str | None = None,
    raw_error_message: str | None = None,
    raw_error_data: Any = None,
    runtime_stage: str | None = None,
```

and pass these fields into `McpFailureEvidence(...)`.

- [ ] **Step 6: Run schema and builder tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_schemas.py tests/adapters/mcp/test_mcp_builder.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/schemas.py" "src/lumiagent/adapters/mcp/builder.py" "tests/adapters/mcp/test_schemas.py" "tests/adapters/mcp/test_mcp_builder.py"
git commit -m @'
Add MCP selection evidence helpers
'@
```

---

### Task 6: MCP Trace Mapper

**Files:**
- Create: `src/lumiagent/adapters/mcp/mapper.py`
- Test: `tests/adapters/mcp/test_mapper.py`

- [ ] **Step 1: Write failing mapper tests**

Create `tests/adapters/mcp/test_mapper.py`:

```python
from lumiagent.adapters.mcp.conventions import MCP_SPAN_TOOL_SELECTION
from lumiagent.adapters.mcp.mapper import McpTraceMapper
from lumiagent.adapters.mcp.runtime import (
    McpConnectionInfo,
    McpRuntimeError,
    McpRuntimeStage,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
)
from lumiagent.adapters.mcp.selector import McpToolSelection
from lumiagent.adapters.mcp.taxonomy import McpFailureType
from lumiagent.tracing import RunStatus, SpanStatus
from lumiagent.tracing.validator import validate_run


def test_mapper_creates_success_agent_run() -> None:
    mapper = McpTraceMapper()
    run = mapper.map_success(
        run_name="filesystem read success",
        connection=McpConnectionInfo(
            transport="stdio",
            server_name="filesystem",
            server_command="npx",
            server_args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        ),
        session=McpSessionInfo(protocol_version="2024-11-05", server_name="filesystem"),
        tools=[McpToolDefinition(name="read_file", input_schema={"type": "object"})],
        selection=McpToolSelection(
            requested_tool_name="read_file",
            selected_tool_name="read_file",
            available_tool_names=["read_file"],
        ),
        result=McpToolCallResult(
            tool_name="read_file",
            arguments={"path": "README.md"},
            content=[{"type": "text", "text": "# LumiAgent"}],
            latency_ms=10,
        ),
    )

    validate_run(run)
    assert run.status is RunStatus.SUCCESS
    assert run.root_spans[0].children[2].metadata["type"] == "mcp_discovery"
    assert run.root_spans[0].children[3].metadata["type"] == MCP_SPAN_TOOL_SELECTION


def test_mapper_creates_failure_agent_run() -> None:
    mapper = McpTraceMapper()
    run = mapper.map_failure(
        run_name="filesystem tool not found",
        connection=McpConnectionInfo(
            transport="stdio",
            server_name="filesystem",
            server_command="npx",
            server_args=[],
        ),
        session=McpSessionInfo(protocol_version="2024-11-05", server_name="filesystem"),
        tools=[McpToolDefinition(name="read_file")],
        requested_tool_name="read_me",
        error=McpRuntimeError(
            failure_type=McpFailureType.TOOL_NOT_FOUND,
            stage=McpRuntimeStage.TOOL_SELECTION,
            message="Tool read_me was not found.",
            raw_error_code="tool_not_found",
            raw_error_data={"available_tools": ["read_file"]},
        ),
    )

    validate_run(run)
    assert run.status is RunStatus.ERROR
    assert run.root_spans[0].status is SpanStatus.ERROR
    assert run.diagnoses[0].failure_type == "tool_not_found"
    assert run.diagnoses[0].evidence_span_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_mapper.py -v
```

Expected: FAIL because `mapper.py` does not exist.

- [ ] **Step 3: Implement mapper**

Create `src/lumiagent/adapters/mcp/mapper.py`:

```python
"""Map MCP runtime outputs into Trace Core runs."""
from __future__ import annotations

from datetime import UTC, datetime

from lumiagent.adapters.mcp.builder import (
    add_mcp_failure_evidence,
    add_mcp_initialization,
    add_mcp_tool_execution,
    add_mcp_tool_result,
    add_mcp_tool_schema_snapshot,
    add_mcp_tool_selection,
    start_mcp_tool_chain,
)
from lumiagent.adapters.mcp.runtime import (
    McpConnectionInfo,
    McpRuntimeError,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
)
from lumiagent.adapters.mcp.selector import McpToolSelection
from lumiagent.tracing import RunStatus, Severity, SpanStatus, TargetType, TraceBuilder


class McpTraceMapper:
    def map_success(
        self,
        *,
        run_name: str,
        connection: McpConnectionInfo,
        session: McpSessionInfo,
        tools: list[McpToolDefinition],
        selection: McpToolSelection,
        result: McpToolCallResult,
    ):
        builder = TraceBuilder(name=run_name, input_value={"transport": connection.transport})
        chain_id = start_mcp_tool_chain(
            builder,
            server_name=connection.server_name,
            metadata={
                "transport": connection.transport,
                "server_command": connection.server_command,
                "server_args": connection.server_args,
            },
        )
        add_mcp_initialization(
            builder,
            chain_id,
            server_name=connection.server_name,
            protocol_version=session.protocol_version,
            capabilities=session.capabilities,
        )
        schema_id = add_mcp_tool_schema_snapshot(
            builder,
            chain_id,
            server_name=connection.server_name,
            captured_at=datetime.now(UTC).isoformat(),
            tools=[tool.model_dump(mode="json") for tool in tools],
        )
        add_mcp_tool_selection(
            builder,
            chain_id,
            server_name=connection.server_name,
            requested_tool_name=selection.requested_tool_name,
            selected_tool_name=selection.selected_tool_name,
            available_tool_names=selection.available_tool_names,
            selection_strategy=selection.selection_strategy,
            reason=selection.reason,
        )
        execution_id = add_mcp_tool_execution(
            builder,
            chain_id,
            server_name=connection.server_name,
            tool_name=result.tool_name,
            arguments=result.arguments,
            schema_artifact_id=schema_id,
            validation={"status": "skipped", "errors": []},
        )
        add_mcp_tool_result(
            builder,
            execution_id,
            content=result.content,
            latency_ms=result.latency_ms,
            status="success",
            metadata={"tool_name": result.tool_name},
        )
        builder.end_span(execution_id, status=SpanStatus.SUCCESS, output={"status": "success"})
        builder.end_span(chain_id, status=SpanStatus.SUCCESS)
        return builder.build(status=RunStatus.SUCCESS, output={"status": "success"})

    def map_failure(
        self,
        *,
        run_name: str,
        connection: McpConnectionInfo,
        session: McpSessionInfo | None,
        tools: list[McpToolDefinition],
        requested_tool_name: str,
        error: McpRuntimeError,
    ):
        builder = TraceBuilder(name=run_name, input_value={"transport": connection.transport})
        chain_id = start_mcp_tool_chain(
            builder,
            server_name=connection.server_name,
            metadata={
                "transport": connection.transport,
                "server_command": connection.server_command,
                "server_args": connection.server_args,
            },
        )
        if session is not None:
            add_mcp_initialization(
                builder,
                chain_id,
                server_name=connection.server_name,
                protocol_version=session.protocol_version,
                capabilities=session.capabilities,
            )
        if tools:
            add_mcp_tool_schema_snapshot(
                builder,
                chain_id,
                server_name=connection.server_name,
                captured_at=datetime.now(UTC).isoformat(),
                tools=[tool.model_dump(mode="json") for tool in tools],
            )
        selection_id = add_mcp_tool_selection(
            builder,
            chain_id,
            server_name=connection.server_name,
            requested_tool_name=requested_tool_name,
            selected_tool_name=None,
            available_tool_names=[tool.name for tool in tools],
            reason=error.message,
            status=SpanStatus.ERROR,
        )
        add_mcp_failure_evidence(
            builder,
            selection_id,
            failure_type=error.failure_type,
            failure_stage=error.stage.value,
            server_name=connection.server_name,
            tool_name=requested_tool_name,
            evidence_span_ids=[selection_id],
            error_code=error.raw_error_code,
            error_message=error.message,
            raw_error_code=error.raw_error_code,
            raw_error_message=error.message,
            raw_error_data=error.raw_error_data,
            runtime_stage=error.stage.value,
        )
        builder.add_diagnosis(
            target_type=TargetType.RUN,
            target_id=builder.run.run_id,
            failure_type=error.failure_type.value,
            severity=Severity.MEDIUM,
            summary=error.message,
            evidence_span_ids=[selection_id],
            suggested_fix="Inspect MCP tool discovery and call configuration.",
        )
        builder.end_span(chain_id, status=SpanStatus.ERROR)
        return builder.build(status=RunStatus.ERROR, output={"status": "error"})
```

- [ ] **Step 4: Run mapper tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_mapper.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/mapper.py" "tests/adapters/mcp/test_mapper.py"
git commit -m @'
Map MCP runtime results to traces
'@
```

---

### Task 7: McpCaptureStrategy Orchestration

**Files:**
- Create: `src/lumiagent/adapters/mcp/capture.py`
- Test: `tests/adapters/mcp/test_capture.py`

- [ ] **Step 1: Write failing capture tests with fake runtime**

Create `tests/adapters/mcp/test_capture.py`:

```python
from typing import Any

import pytest
from pydantic import ValidationError

from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
from lumiagent.adapters.mcp.runtime import (
    McpConnectionInfo,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
)
from lumiagent.tracing import RunStatus
from lumiagent.tracing.validator import validate_run


class FakeRuntime:
    def __init__(self) -> None:
        self.closed = False

    def connect(self) -> McpConnectionInfo:
        return McpConnectionInfo(
            transport="stdio",
            server_name="filesystem",
            server_command="npx",
            server_args=[],
        )

    def initialize(self) -> McpSessionInfo:
        return McpSessionInfo(protocol_version="2024-11-05", server_name="filesystem")

    def list_tools(self) -> list[McpToolDefinition]:
        return [McpToolDefinition(name="read_file", input_schema={"type": "object"})]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult:
        return McpToolCallResult(
            tool_name=name,
            arguments=arguments,
            content=[{"type": "text", "text": "# LumiAgent"}],
            latency_ms=1,
        )

    def close(self) -> None:
        self.closed = True


def test_capture_config_requires_json_object_arguments() -> None:
    with pytest.raises(ValidationError):
        McpCaptureConfig(
            transport="stdio",
            server_command="npx",
            server_args=[],
            tool_name="read_file",
            arguments=[],
            output_path="trace.json",
        )


def test_capture_strategy_creates_success_trace_and_closes_runtime() -> None:
    runtime = FakeRuntime()
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            transport="stdio",
            server_command="npx",
            server_args=[],
            tool_name="read_file",
            arguments={"path": "README.md"},
            output_path="trace.json",
        ),
        runtime=runtime,
    )

    run = strategy.capture()

    validate_run(run)
    assert run.status is RunStatus.SUCCESS
    assert runtime.closed is True


def test_capture_strategy_creates_tool_not_found_trace() -> None:
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            transport="stdio",
            server_command="npx",
            server_args=[],
            tool_name="read_me",
            arguments={"path": "README.md"},
            output_path="trace.json",
        ),
        runtime=FakeRuntime(),
    )

    run = strategy.capture()

    validate_run(run)
    assert run.status is RunStatus.ERROR
    assert run.diagnoses[0].failure_type == "tool_not_found"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_capture.py -v
```

Expected: FAIL because `capture.py` does not exist.

- [ ] **Step 3: Implement config and strategy**

Create `src/lumiagent/adapters/mcp/capture.py`:

```python
"""MCP capture strategy."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from lumiagent.adapters.mcp.mapper import McpTraceMapper
from lumiagent.adapters.mcp.runtime import (
    McpClientRuntime,
    McpRuntimeError,
    McpRuntimeStage,
    StdioMcpClientRuntime,
)
from lumiagent.adapters.mcp.selector import ExplicitToolSelector
from lumiagent.adapters.mcp.taxonomy import McpFailureType


class McpCaptureConfig(BaseModel):
    transport: str = "stdio"
    server_command: str
    server_args: list[str] = Field(default_factory=list)
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_path: str
    timeout_seconds: int = Field(default=30, ge=1)
    server_name: str | None = None

    @field_validator("transport")
    @classmethod
    def require_stdio_transport(cls, value: str) -> str:
        if value != "stdio":
            raise ValueError("only stdio transport is supported in Phase 2b")
        return value

    @field_validator("server_command", "tool_name", "output_path")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class McpCaptureStrategy:
    def __init__(
        self,
        *,
        config: McpCaptureConfig,
        runtime: McpClientRuntime | None = None,
        selector: ExplicitToolSelector | None = None,
        mapper: McpTraceMapper | None = None,
    ) -> None:
        self.config = config
        self.runtime = runtime or StdioMcpClientRuntime(
            server_command=config.server_command,
            server_args=config.server_args,
            server_name=config.server_name,
            timeout_seconds=config.timeout_seconds,
        )
        self.selector = selector or ExplicitToolSelector()
        self.mapper = mapper or McpTraceMapper()

    def capture(self):
        connection = self.runtime.connect()
        session = None
        tools = []
        try:
            session = self.runtime.initialize()
            tools = self.runtime.list_tools()
            selection = self.selector.select(
                requested_tool_name=self.config.tool_name,
                tools=tools,
            )
            result = self.runtime.call_tool(selection.selected_tool_name, self.config.arguments)
            return self.mapper.map_success(
                run_name=f"MCP capture: {self.config.tool_name}",
                connection=connection,
                session=session,
                tools=tools,
                selection=selection,
                result=result,
            )
        except ValueError as exc:
            error = McpRuntimeError(
                failure_type=McpFailureType.TOOL_NOT_FOUND,
                stage=McpRuntimeStage.TOOL_SELECTION,
                message=str(exc),
                raw_error_code=McpFailureType.TOOL_NOT_FOUND.value,
                raw_error_data={"available_tools": [tool.name for tool in tools]},
            )
            return self.mapper.map_failure(
                run_name=f"MCP capture failed: {self.config.tool_name}",
                connection=connection,
                session=session,
                tools=tools,
                requested_tool_name=self.config.tool_name,
                error=error,
            )
        except McpRuntimeError as exc:
            return self.mapper.map_failure(
                run_name=f"MCP capture failed: {self.config.tool_name}",
                connection=connection,
                session=session,
                tools=tools,
                requested_tool_name=self.config.tool_name,
                error=exc,
            )
        finally:
            self.runtime.close()
```

- [ ] **Step 4: Run capture tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_capture.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/capture.py" "tests/adapters/mcp/test_capture.py"
git commit -m @'
Add MCP capture strategy
'@
```

---

### Task 8: MCP Viewer Summary

**Files:**
- Create: `src/lumiagent/adapters/mcp/viewer.py`
- Test: `tests/adapters/mcp/test_viewer.py`

- [ ] **Step 1: Write failing viewer tests**

Create `tests/adapters/mcp/test_viewer.py`:

```python
from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
from lumiagent.adapters.mcp.viewer import render_mcp_trace_summary
from tests.adapters.mcp.test_capture import FakeRuntime


def test_viewer_renders_success_trace_summary() -> None:
    run = McpCaptureStrategy(
        config=McpCaptureConfig(
            transport="stdio",
            server_command="npx",
            server_args=[],
            tool_name="read_file",
            arguments={"path": "README.md"},
            output_path="trace.json",
        ),
        runtime=FakeRuntime(),
    ).capture()

    output = "\n".join(render_mcp_trace_summary(run))

    assert "Run:" in output
    assert "Status: success" in output
    assert "MCP Tool Chain" in output
    assert "Tool Selection" in output
    assert "requested: read_file" in output
    assert "selected: read_file" in output


def test_viewer_renders_failure_trace_summary() -> None:
    run = McpCaptureStrategy(
        config=McpCaptureConfig(
            transport="stdio",
            server_command="npx",
            server_args=[],
            tool_name="read_me",
            arguments={"path": "README.md"},
            output_path="trace.json",
        ),
        runtime=FakeRuntime(),
    ).capture()

    output = "\n".join(render_mcp_trace_summary(run))

    assert "Status: error" in output
    assert "MCP Failure" in output
    assert "type: tool_not_found" in output
    assert "requested tool: read_me" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_viewer.py -v
```

Expected: FAIL because `viewer.py` does not exist.

- [ ] **Step 3: Implement viewer**

Create `src/lumiagent/adapters/mcp/viewer.py`:

```python
"""Render MCP trace summaries for CLI output."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from lumiagent.adapters.mcp.conventions import MCP_ARTIFACT_TOOL_SELECTION
from lumiagent.tracing import AgentRun, Span


def render_mcp_trace_summary(run: AgentRun) -> list[str]:
    lines = [f"Run: {run.name}", f"Status: {run.status.value}", "", "Span Tree:"]
    for root in run.root_spans:
        lines.extend(_render_span(root, depth=0))
    selection = _first_artifact_content(run, MCP_ARTIFACT_TOOL_SELECTION)
    if selection:
        lines.extend([
            "",
            "Tool Selection:",
            f"  strategy: {selection.get('selection_strategy')}",
            f"  requested: {selection.get('requested_tool_name')}",
            f"  selected: {selection.get('selected_tool_name')}",
        ])
    if run.diagnoses:
        diagnosis = run.diagnoses[0]
        lines.extend([
            "",
            "MCP Failure:",
            f"  type: {diagnosis.failure_type}",
            f"  requested tool: {selection.get('requested_tool_name') if selection else ''}",
            f"  evidence spans: {', '.join(diagnosis.evidence_span_ids)}",
        ])
    return lines


def _render_span(span: Span, *, depth: int) -> list[str]:
    indent = "  " * depth
    lines = [f"{indent}- {span.name} [{span.status.value}]"]
    for child in span.children:
        lines.extend(_render_span(child, depth=depth + 1))
    return lines


def _iter_spans(spans: list[Span]) -> Iterator[Span]:
    for span in spans:
        yield span
        yield from _iter_spans(span.children)


def _first_artifact_content(run: AgentRun, artifact_type: str) -> dict[str, Any] | None:
    for span in _iter_spans(run.root_spans):
        for artifact in span.artifacts:
            if artifact.metadata.get("type") == artifact_type and isinstance(artifact.content, dict):
                return artifact.content
    return None
```

- [ ] **Step 4: Run viewer tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_viewer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/viewer.py" "tests/adapters/mcp/test_viewer.py"
git commit -m @'
Add MCP trace viewer summary
'@
```

---

### Task 9: CLI Capture and Show Commands

**Files:**
- Modify: `src/lumiagent/cli.py`
- Create: `tests/test_cli_mcp.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli_mcp.py`:

```python
import json
from pathlib import Path

from typer.testing import CliRunner

from lumiagent.cli import app

runner = CliRunner()


def test_capture_mcp_rejects_invalid_arguments_json() -> None:
    result = runner.invoke(
        app,
        [
            "capture",
            "mcp",
            "--transport",
            "stdio",
            "--server-command",
            "npx",
            "--tool",
            "read_file",
            "--arguments",
            "not-json",
            "-o",
            "trace.json",
        ],
    )

    assert result.exit_code != 0
    assert "arguments must be a JSON object" in result.output


def test_show_renders_trace_file(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "run_id": "run_cli",
                "name": "cli trace",
                "status": "success",
                "started_at": "2026-05-27T00:00:00Z",
                "ended_at": "2026-05-27T00:00:01Z",
                "input": None,
                "output": None,
                "metadata": {},
                "parent_run_id": None,
                "triggered_by_span_id": None,
                "root_spans": [],
                "evaluations": [],
                "diagnoses": [],
                "annotations": [],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["show", str(trace_path)])

    assert result.exit_code == 0
    assert "Run: cli trace" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/test_cli_mcp.py -v
```

Expected: FAIL because `capture` and `show` commands do not exist.

- [ ] **Step 3: Add CLI commands**

Modify `src/lumiagent/cli.py` after `console = Console()`:

```python
capture_app = typer.Typer(help="Capture traces from external systems.")
app.add_typer(capture_app, name="capture")
```

Add imports near top:

```python
import json
from pathlib import Path
from typing import Any
```

Replace existing `from typing import Optional` with:

```python
from typing import Any, Optional
```

Add before `if __name__ == "__main__":`:

```python
@capture_app.command("mcp")
def capture_mcp(
    transport: str = typer.Option(..., help="MCP transport. Phase 2b supports stdio."),
    server_command: str = typer.Option(..., help="MCP server command."),
    server_arg: list[str] = typer.Option([], "--server-arg", help="MCP server argument."),
    tool: str = typer.Option(..., help="MCP tool name to call."),
    arguments: str = typer.Option("{}", help="Tool arguments as a JSON object."),
    output: Path = typer.Option(..., "--output", "-o", help="Trace JSON output path."),
    timeout_seconds: int = typer.Option(30, help="MCP operation timeout in seconds."),
) -> None:
    parsed_arguments = _parse_json_object(arguments)
    from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
    from lumiagent.tracing import to_json

    config = McpCaptureConfig(
        transport=transport,
        server_command=server_command,
        server_args=server_arg,
        tool_name=tool,
        arguments=parsed_arguments,
        output_path=str(output),
        timeout_seconds=timeout_seconds,
    )
    run = McpCaptureStrategy(config=config).capture()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(to_json(run), encoding="utf-8")
    console.print(f"Trace written to [cyan]{output}[/cyan]")


@app.command("show")
def show_trace(trace_path: Path = typer.Argument(..., help="Trace JSON path.")) -> None:
    from lumiagent.adapters.mcp.viewer import render_mcp_trace_summary
    from lumiagent.tracing import from_json

    run = from_json(trace_path.read_text(encoding="utf-8"))
    for line in render_mcp_trace_summary(run):
        console.print(line)


def _parse_json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("arguments must be a JSON object") from exc
    if not isinstance(value, dict):
        raise typer.BadParameter("arguments must be a JSON object")
    return value
```

Ensure import order satisfies ruff.

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/test_cli_mcp.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/cli.py" "tests/test_cli_mcp.py"
git commit -m @'
Add MCP capture CLI commands
'@
```

---

### Task 10: Real Stdio MCP Runtime

**Files:**
- Modify: `src/lumiagent/adapters/mcp/runtime.py`
- Test: `tests/adapters/mcp/test_runtime.py`

- [ ] **Step 1: Inspect project dependencies**

Read `pyproject.toml`. If an MCP SDK dependency already exists, use it. If not, add the official Python MCP SDK dependency only if available in the environment and needed for real stdio communication. Do not implement a custom JSON-RPC client unless the SDK cannot be used.

- [ ] **Step 2: Add a guarded construction test only**

Append to `tests/adapters/mcp/test_runtime.py`:

```python
def test_stdio_runtime_exposes_runtime_methods() -> None:
    runtime = StdioMcpClientRuntime(server_command="npx", server_args=[])

    assert callable(runtime.connect)
    assert callable(runtime.initialize)
    assert callable(runtime.list_tools)
    assert callable(runtime.call_tool)
    assert callable(runtime.close)
```

Do not add a unit test that starts a third-party server. Real server verification is manual/executable in Task 13.

- [ ] **Step 3: Implement stdio runtime using MCP SDK or subprocess-backed session**

Replace `NotImplementedError` methods in `StdioMcpClientRuntime` with a real stdio MCP client. Preserve this public behavior:

```python
runtime = StdioMcpClientRuntime(
    server_command="npx",
    server_args=["-y", "@modelcontextprotocol/server-filesystem", "."],
    server_name="filesystem",
    timeout_seconds=30,
)
connection = runtime.connect()
session = runtime.initialize()
tools = runtime.list_tools()
result = runtime.call_tool("read_file", {"path": "README.md"})
runtime.close()
```

Mapping requirements:

- Server launch failure raises `McpRuntimeError(failure_type=CONNECTION_FAILED, stage=CONNECTION, ...)`.
- Initialize failure raises `INITIALIZATION_FAILED` at `INITIALIZATION`.
- Tool listing failure raises `TOOL_DISCOVERY_FAILED` at `TOOL_DISCOVERY`.
- Tool call timeout raises `TIMEOUT` at `TOOL_EXECUTION`.
- Tool call MCP error raises `TOOL_EXECUTION_FAILED` at `TOOL_EXECUTION`, unless message clearly indicates permission denied.
- Early process/transport close raises `TRANSPORT_INTERRUPTED`.
- Unparseable result shape raises `RESULT_INVALID`.

If the SDK is async-only, keep the runtime protocol synchronous by using `asyncio.run` internally, but do not call `asyncio.run` if already inside an event loop; in that case document the limitation in the technical report and keep CLI sync.

- [ ] **Step 4: Run runtime tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_runtime.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/runtime.py" "tests/adapters/mcp/test_runtime.py" "pyproject.toml" "uv.lock" "poetry.lock"
git commit -m @'
Implement stdio MCP runtime
'@
```

Only include dependency lock files that actually exist and changed.

---

### Task 11: Adapter Public Exports and Full Unit Suite

**Files:**
- Modify: `src/lumiagent/adapters/mcp/__init__.py`
- Test: existing adapter tests

- [ ] **Step 1: Add public export assertions to an existing test**

Append to `tests/adapters/mcp/test_taxonomy.py`:

```python
def test_mcp_capture_apis_are_public() -> None:
    from lumiagent.adapters.mcp import (
        ExplicitToolSelector,
        McpCaptureConfig,
        McpCaptureStrategy,
        McpClientRuntime,
        McpTraceMapper,
        StdioMcpClientRuntime,
    )

    assert McpCaptureConfig.__name__ == "McpCaptureConfig"
    assert McpCaptureStrategy.__name__ == "McpCaptureStrategy"
    assert McpClientRuntime.__name__ == "McpClientRuntime"
    assert StdioMcpClientRuntime.__name__ == "StdioMcpClientRuntime"
    assert ExplicitToolSelector.__name__ == "ExplicitToolSelector"
    assert McpTraceMapper.__name__ == "McpTraceMapper"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp/test_taxonomy.py::test_mcp_capture_apis_are_public -v
```

Expected: FAIL because exports are missing.

- [ ] **Step 3: Update adapter exports**

Update `src/lumiagent/adapters/mcp/__init__.py` to export existing Phase 2a APIs plus:

```python
from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
from lumiagent.adapters.mcp.mapper import McpTraceMapper
from lumiagent.adapters.mcp.runtime import McpClientRuntime, StdioMcpClientRuntime
from lumiagent.adapters.mcp.selector import ExplicitToolSelector
```

Add the names to `__all__`.

- [ ] **Step 4: Run adapter tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/mcp -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add "src/lumiagent/adapters/mcp/__init__.py" "tests/adapters/mcp/test_taxonomy.py"
git commit -m @'
Export MCP capture APIs
'@
```

---

### Task 12: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Update README project structure and roadmap**

In both README files, update the project structure to include:

```text
src/lumiagent/
├── capture/
│   ├── __init__.py
│   └── strategy.py
├── adapters/
│   └── mcp/
│       ├── capture.py
│       ├── runtime.py
│       ├── selector.py
│       ├── mapper.py
│       ├── viewer.py
│       ├── builder.py
│       ├── conventions.py
│       ├── schemas.py
│       └── taxonomy.py
```

Do not mark Phase 2b complete until Task 13 verification passes.

- [ ] **Step 2: Add capture command example to README**

Add a short Phase 2b usage example to both README files after the existing quick example:

```powershell
lumiagent capture mcp `
  --transport stdio `
  --server-command "npx" `
  --server-arg "-y" `
  --server-arg "@modelcontextprotocol/server-filesystem" `
  --server-arg "D:\Projects\github\lumiagent" `
  --tool "read_file" `
  --arguments "{\"path\":\"README.md\"}" `
  -o ".lumiagent/traces/filesystem-read-success.json"

lumiagent show ".lumiagent/traces/filesystem-read-success.json"
```

- [ ] **Step 3: Commit docs**

```powershell
git add "README.md" "README.zh-CN.md"
git commit -m @'
Document MCP capture CLI path
'@
```

---

### Task 13: Full Verification and Real Third-Party MCP Check

**Files:**
- Create: `.lumiagent/traces/filesystem-read-success.json` only if the project wants committed sanitized examples; otherwise leave `.lumiagent/` untracked.
- Create: `.lumiagent/traces/filesystem-tool-not-found.json` only if the project wants committed sanitized examples; otherwise leave `.lumiagent/` untracked.
- Create: `docs/reports/mcp-capture-display-chain-technical-report.zh-CN.md`

- [ ] **Step 1: Run unit verification**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest -v
```

Expected: PASS.

- [ ] **Step 2: Run ruff**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture tests/tracing tests/adapters tests/capture tests/test_cli_mcp.py
```

Expected: PASS.

- [ ] **Step 3: Run mypy**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture
```

Expected: PASS.

- [ ] **Step 4: Run real filesystem MCP success capture**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli capture mcp `
  --transport stdio `
  --server-command "npx" `
  --server-arg "-y" `
  --server-arg "@modelcontextprotocol/server-filesystem" `
  --server-arg "D:\Projects\github\lumiagent" `
  --tool "read_file" `
  --arguments "{\"path\":\"README.md\"}" `
  -o ".lumiagent/traces/filesystem-read-success.json"
```

Expected: command writes `.lumiagent/traces/filesystem-read-success.json` and reports trace path.

- [ ] **Step 5: Show success trace**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli show ".lumiagent/traces/filesystem-read-success.json"
```

Expected output includes `Status: success`, `MCP Tool Chain`, `Tool Selection`, `requested: read_file`, and `selected: read_file`.

- [ ] **Step 6: Run real filesystem MCP failure capture**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli capture mcp `
  --transport stdio `
  --server-command "npx" `
  --server-arg "-y" `
  --server-arg "@modelcontextprotocol/server-filesystem" `
  --server-arg "D:\Projects\github\lumiagent" `
  --tool "read_me" `
  --arguments "{\"path\":\"README.md\"}" `
  -o ".lumiagent/traces/filesystem-tool-not-found.json"
```

Expected: command writes `.lumiagent/traces/filesystem-tool-not-found.json`. It may exit non-zero if CLI chooses to signal capture failure, but the trace file must exist.

- [ ] **Step 7: Show failure trace**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli show ".lumiagent/traces/filesystem-tool-not-found.json"
```

Expected output includes `Status: error`, `MCP Failure`, `type: tool_not_found`, and `requested tool: read_me`.

- [ ] **Step 8: Write Chinese technical report**

Create `docs/reports/mcp-capture-display-chain-technical-report.zh-CN.md` with these sections:

```markdown
# MCP Capture + Display Chain 技术报告

## 背景与产品价值

## 需求范围与非目标

## 技术选择

## 架构与设计模式

## 实现要点

## 第三方 MCP 验证结果

## 自动化验证结果

## 兼容性与扩展性

## 风险、权衡与后续建议
```

The report must state whether the real filesystem MCP success/failure commands were run. If they failed because of environment, include the exact failure and whether unit tests still passed.

- [ ] **Step 9: Commit verification report**

```powershell
git add "docs/reports/mcp-capture-display-chain-technical-report.zh-CN.md"
git commit -m @'
Add MCP capture display technical report
'@
```

Do not commit `.lumiagent/traces/*.json` unless the user explicitly approves committing sanitized generated examples.

---

## Self-Review Checklist

- Spec coverage: Tasks 1-13 cover CaptureStrategy, runtime, stdio implementation, selector, mapper, taxonomy, CLI capture/show, viewer, tests, real third-party verification, and technical report.
- Placeholder scan: No task uses TBD/TODO/fill-in placeholders; Task 10 contains an implementation decision point for the MCP SDK because dependency availability must be verified during implementation.
- Type consistency: The plan consistently uses `McpCaptureConfig`, `McpCaptureStrategy`, `McpClientRuntime`, `StdioMcpClientRuntime`, `ExplicitToolSelector`, `McpToolSelection`, `McpTraceMapper`, `McpRuntimeError`, and `McpRuntimeStage`.
- Scope check: HTTP/SSE, automatic LLM selection, Claude Code hooks, proxy, and Web UI remain out of scope.
