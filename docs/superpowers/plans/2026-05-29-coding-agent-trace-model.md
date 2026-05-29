# Coding Agent Trace Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 3 Coding Agent Trace Model: generic semantic coding trace conventions, Claude Code hooks capture, minimal transcript enrichment, TraceWriter-based conversion, workflow checks, CLI review, fixtures, verification, and technical report.

**Architecture:** Add framework-agnostic Coding Agent semantics under `src/lumiagent/adapters/coding/`, Claude Code-specific capture under `src/lumiagent/adapters/claude_code/`, and a minimal `BuilderTraceWriter` under `src/lumiagent/tracing/`. Keep MCP capture on its existing `McpTraceMapper` path while routing Phase 3 incremental hooks conversion through `TraceWriter`.

**Tech Stack:** Python 3.11+, Pydantic, Typer, Rich, pytest, ruff, mypy, existing LumiAgent Trace Core.

---

## File Structure

Create:

- `src/lumiagent/adapters/coding/__init__.py` — exports Coding Agent conventions, schemas, normalizer, validator, and viewer helpers.
- `src/lumiagent/adapters/coding/conventions.py` — stable Phase 3 convention constants and metadata helpers.
- `src/lumiagent/adapters/coding/events.py` — Pydantic schemas for normalized coding events, evidence, and workflow findings.
- `src/lumiagent/adapters/coding/normalizer.py` — maps source tool/action events to semantic coding conventions.
- `src/lumiagent/adapters/coding/validator.py` — deterministic workflow checks over `AgentRun`.
- `src/lumiagent/adapters/coding/viewer.py` — Coding Agent trace renderer for `lumiagent show`.
- `src/lumiagent/adapters/claude_code/__init__.py` — exports Claude Code adapter API.
- `src/lumiagent/adapters/claude_code/events.py` — LumiAgent-owned hook event schemas and JSONL reader/writer helpers.
- `src/lumiagent/adapters/claude_code/transcript.py` — minimal best-effort transcript enrichment.
- `src/lumiagent/adapters/claude_code/sanitizer.py` — sanitizer for fixtures and optional trace output.
- `src/lumiagent/adapters/claude_code/converter.py` — events/transcript to `AgentRun` converter using `TraceWriter`.
- `src/lumiagent/adapters/claude_code/setup.py` — `.claude/settings.json` merge/setup behavior.
- `src/lumiagent/adapters/claude_code/hooks.py` — hook payload ingestion entrypoint helpers.
- `src/lumiagent/tracing/builder_writer.py` — minimal `TraceWriter` implementation backed by `TraceBuilder`.
- `tests/adapters/coding/test_conventions.py`
- `tests/adapters/coding/test_schemas.py`
- `tests/adapters/coding/test_normalizer.py`
- `tests/adapters/coding/test_validator.py`
- `tests/adapters/coding/test_viewer.py`
- `tests/adapters/claude_code/test_events.py`
- `tests/adapters/claude_code/test_transcript.py`
- `tests/adapters/claude_code/test_sanitizer.py`
- `tests/adapters/claude_code/test_converter.py`
- `tests/adapters/claude_code/test_setup.py`
- `tests/tracing/test_builder_writer.py`
- `tests/test_cli_coding_trace.py`
- `tests/adapters/coding/fixtures/coding_trace_success.json`
- `tests/adapters/coding/fixtures/coding_trace_missing_verification.json`
- `tests/adapters/coding/fixtures/coding_trace_failed_test_recovered.json`
- `tests/adapters/coding/fixtures/coding_trace_permission_denied.json`
- `tests/adapters/claude_code/fixtures/real_session_sanitized_trace.json`
- `docs/reports/coding-agent-trace-model-technical-report.zh-CN.md`

Modify:

- `src/lumiagent/tracing/__init__.py` — export `BuilderTraceWriter`.
- `src/lumiagent/cli.py` — add `setup claude-code`, `trace`, `show --checks`, and route Coding Agent traces to coding viewer.
- `.gitignore` — ignore local raw `.lumiagent/sessions/` and `.lumiagent/traces/*-raw.json` if not already covered.

---

### Task 1: Coding Agent Conventions

**Files:**
- Create: `src/lumiagent/adapters/coding/__init__.py`
- Create: `src/lumiagent/adapters/coding/conventions.py`
- Test: `tests/adapters/coding/test_conventions.py`

- [ ] **Step 1: Write failing tests for stable convention constants**

Create `tests/adapters/coding/test_conventions.py`:

```python
from lumiagent.adapters.coding.conventions import (
    CODING_DOMAIN,
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_CONVENTIONS,
    CODING_CONTEXT_GATHERING,
    CODING_CODE_EDIT,
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
    assert CODING_CONVENTIONS == {
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
    }


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
```

- [ ] **Step 2: Run convention tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_conventions.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'lumiagent.adapters.coding'`.

- [ ] **Step 3: Implement coding conventions**

Create `src/lumiagent/adapters/coding/conventions.py`:

```python
"""Coding Agent trace conventions."""
from __future__ import annotations

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
    if source_ids:
        metadata["source_event_ids"] = source_ids
    if evidence_types:
        metadata["evidence_types"] = evidence_types
    if classification_reason is not None:
        metadata["classification"] = {
            "strategy": "rule",
            "reason": classification_reason,
        }
    if extra:
        metadata.update(extra)
    return metadata
```

Create `src/lumiagent/adapters/coding/__init__.py`:

```python
"""Coding Agent trace adapter."""
from lumiagent.adapters.coding.conventions import (
    CODING_APPROVAL_DECISION,
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_ARTIFACT_WORKFLOW_FINDING,
    CODING_CODE_EDIT,
    CODING_CONTEXT_GATHERING,
    CODING_CONVENTIONS,
    CODING_DOMAIN,
    CODING_ERROR_OBSERVED,
    CODING_FAILURE_RECOVERY,
    CODING_FILE_READ,
    CODING_FILE_SEARCH,
    CODING_FINAL_RESPONSE,
    CODING_GIT_DIFF,
    CODING_PERMISSION_REQUEST,
    CODING_RESULT_INTERPRETATION,
    CODING_SHELL_COMMAND,
    CODING_TASK_UNDERSTANDING,
    CODING_TEST_RUN,
    CODING_USER_PROMPT,
    CODING_VERIFICATION,
    CODING_WORKFLOW_CHECK,
    coding_metadata,
)

__all__ = [
    "CODING_APPROVAL_DECISION",
    "CODING_ARTIFACT_ACTION_EVIDENCE",
    "CODING_ARTIFACT_SEMANTIC_EVIDENCE",
    "CODING_ARTIFACT_WORKFLOW_CHECKS",
    "CODING_ARTIFACT_WORKFLOW_FINDING",
    "CODING_CODE_EDIT",
    "CODING_CONTEXT_GATHERING",
    "CODING_CONVENTIONS",
    "CODING_DOMAIN",
    "CODING_ERROR_OBSERVED",
    "CODING_FAILURE_RECOVERY",
    "CODING_FILE_READ",
    "CODING_FILE_SEARCH",
    "CODING_FINAL_RESPONSE",
    "CODING_GIT_DIFF",
    "CODING_PERMISSION_REQUEST",
    "CODING_RESULT_INTERPRETATION",
    "CODING_SHELL_COMMAND",
    "CODING_TASK_UNDERSTANDING",
    "CODING_TEST_RUN",
    "CODING_USER_PROMPT",
    "CODING_VERIFICATION",
    "CODING_WORKFLOW_CHECK",
    "coding_metadata",
]
```

- [ ] **Step 4: Run convention tests and verify they pass**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_conventions.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/lumiagent/adapters/coding/__init__.py src/lumiagent/adapters/coding/conventions.py tests/adapters/coding/test_conventions.py
git commit -m "Add coding agent trace conventions"
```

---

### Task 2: Coding Event and Evidence Schemas

**Files:**
- Create: `src/lumiagent/adapters/coding/events.py`
- Modify: `src/lumiagent/adapters/coding/__init__.py`
- Test: `tests/adapters/coding/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/adapters/coding/test_schemas.py`:

```python
from lumiagent.adapters.coding.events import (
    CodingActionEvidence,
    CodingSemanticEvidence,
    CodingWorkflowChecks,
    CodingWorkflowFinding,
    NormalizedCodingEvent,
)


def test_action_evidence_defaults_to_raw_redaction() -> None:
    evidence = CodingActionEvidence(
        tool_name="Bash",
        arguments={"command": "python -m pytest -v"},
        result={"status": "success", "exit_code": 0},
    )

    assert evidence.artifact_type == "coding_action_evidence"
    assert evidence.schema_version == "coding_action_evidence.v1"
    assert evidence.safety == {"redaction_state": "raw"}


def test_semantic_evidence_records_summary_and_confidence() -> None:
    evidence = CodingSemanticEvidence(
        convention="task_understanding",
        role="assistant",
        content_summary="Inspect tests and package layout.",
        confidence="medium",
    )

    assert evidence.artifact_type == "coding_semantic_evidence"
    assert evidence.source == "transcript_enrichment"
    assert evidence.content is None


def test_normalized_event_links_source_events_and_evidence() -> None:
    event = NormalizedCodingEvent(
        event_id="coding_evt_1",
        source_event_ids=["evt_1"],
        session_id="session_1",
        sequence=1,
        convention="test_run",
        status="success",
        name="Run pytest",
        action_evidence=CodingActionEvidence(tool_name="Bash"),
        metadata={"classification_reason": "pytest command"},
    )

    assert event.convention == "test_run"
    assert event.action_evidence is not None
    assert event.semantic_evidence is None


def test_workflow_checks_aggregate_status() -> None:
    finding = CodingWorkflowFinding(
        rule_id="code_edit_requires_verification",
        status="failed",
        severity="warning",
        summary="Code was edited without verification.",
        evidence_span_ids=["span_1"],
    )
    checks = CodingWorkflowChecks(status="warning", findings=[finding])

    assert checks.schema_version == "coding_workflow_checks.v1"
    assert checks.findings[0].confidence == "high"
```

- [ ] **Step 2: Run schema tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_schemas.py -v
```

Expected: FAIL because `lumiagent.adapters.coding.events` does not exist.

- [ ] **Step 3: Implement schema models**

Create `src/lumiagent/adapters/coding/events.py`:

```python
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
```

Modify `src/lumiagent/adapters/coding/__init__.py` to export the new schema names:

```python
from lumiagent.adapters.coding.events import (
    CodingActionEvidence,
    CodingSemanticEvidence,
    CodingWorkflowChecks,
    CodingWorkflowFinding,
    NormalizedCodingEvent,
)
```

Add these strings to `__all__`:

```python
"CodingActionEvidence",
"CodingSemanticEvidence",
"CodingWorkflowChecks",
"CodingWorkflowFinding",
"NormalizedCodingEvent",
```

- [ ] **Step 4: Run schema tests and convention tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_conventions.py tests/adapters/coding/test_schemas.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/lumiagent/adapters/coding/__init__.py src/lumiagent/adapters/coding/events.py tests/adapters/coding/test_schemas.py
git commit -m "Add coding trace evidence schemas"
```

---

### Task 3: BuilderTraceWriter

**Files:**
- Create: `src/lumiagent/tracing/builder_writer.py`
- Modify: `src/lumiagent/tracing/__init__.py`
- Test: `tests/tracing/test_builder_writer.py`

- [ ] **Step 1: Write failing writer tests**

Create `tests/tracing/test_builder_writer.py`:

```python
from lumiagent.tracing import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder_writer import BuilderTraceWriter


def test_builder_trace_writer_builds_run_incrementally() -> None:
    writer = BuilderTraceWriter()
    run_id = writer.start_run(name="Coding task", input_value={"task": "fix tests"})
    root_id = writer.start_span("Coding Agent Run", kind=SpanKind.CUSTOM)
    child_id = writer.start_span(
        "Run pytest",
        kind=SpanKind.TOOL,
        parent_span_id=root_id,
        input_value={"command": "python -m pytest -v"},
        metadata={"type": "test_run"},
    )

    event_id = writer.add_event(
        child_id,
        name="command_finished",
        level=EventLevel.INFO,
        message="pytest passed",
    )
    artifact_id = writer.add_artifact(
        child_id,
        name="Action Evidence",
        kind=ArtifactKind.JSON,
        content={"exit_code": 0},
        metadata={"type": "coding_action_evidence"},
    )
    writer.end_span(child_id, status=SpanStatus.SUCCESS, output={"exit_code": 0})
    writer.end_span(root_id, status=SpanStatus.SUCCESS)
    run = writer.flush(status=RunStatus.SUCCESS, output={"status": "success"})

    assert run.run_id == run_id
    assert run.root_spans[0].children[0].span_id == child_id
    assert run.root_spans[0].children[0].events[0].event_id == event_id
    assert run.root_spans[0].children[0].artifacts[0].artifact_id == artifact_id
    assert run.status == RunStatus.SUCCESS


def test_builder_trace_writer_requires_start_run_before_span() -> None:
    writer = BuilderTraceWriter()

    try:
        writer.start_span("orphan")
    except RuntimeError as exc:
        assert "start_run" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
```

- [ ] **Step 2: Run writer tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/tracing/test_builder_writer.py -v
```

Expected: FAIL because `lumiagent.tracing.builder_writer` does not exist.

- [ ] **Step 3: Implement BuilderTraceWriter**

Create `src/lumiagent/tracing/builder_writer.py`:

```python
"""TraceWriter implementation backed by TraceBuilder."""
from __future__ import annotations

from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.enums import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.models import AgentRun, TraceValue


class BuilderTraceWriter:
    def __init__(self) -> None:
        self._builder: TraceBuilder | None = None

    def start_run(
        self,
        *,
        name: str,
        input_value: TraceValue = None,
        metadata: dict[str, object] | None = None,
    ) -> str:
        self._builder = TraceBuilder(name=name, input_value=input_value)
        if metadata:
            self._builder.run.metadata.update(metadata)
        return self._builder.run.run_id

    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.CUSTOM,
        parent_span_id: str | None = None,
        input_value: TraceValue = None,
        metadata: dict[str, object] | None = None,
    ) -> str:
        return self._require_builder().start_span(
            name,
            kind=kind,
            parent_span_id=parent_span_id,
            input_value=input_value,
            metadata=dict(metadata or {}),
        )

    def end_span(
        self,
        span_id: str,
        *,
        status: SpanStatus = SpanStatus.SUCCESS,
        output: TraceValue = None,
    ) -> None:
        self._require_builder().end_span(span_id, status=status, output=output)

    def add_event(
        self,
        span_id: str,
        *,
        name: str,
        level: EventLevel = EventLevel.INFO,
        message: str = "",
        metadata: dict[str, object] | None = None,
    ) -> str:
        return self._require_builder().add_event(
            span_id,
            name=name,
            level=level,
            message=message,
            metadata=dict(metadata or {}),
        )

    def add_artifact(
        self,
        span_id: str,
        *,
        name: str,
        kind: ArtifactKind = ArtifactKind.CUSTOM,
        content: TraceValue = None,
        uri: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> str:
        return self._require_builder().add_artifact(
            span_id,
            name=name,
            kind=kind,
            content=content,
            uri=uri,
            metadata=dict(metadata or {}),
        )

    def flush(
        self,
        *,
        status: RunStatus = RunStatus.SUCCESS,
        output: TraceValue = None,
    ) -> AgentRun:
        return self._require_builder().build(status=status, output=output)

    def _require_builder(self) -> TraceBuilder:
        if self._builder is None:
            raise RuntimeError("start_run must be called before writing trace data")
        return self._builder
```

Modify `src/lumiagent/tracing/__init__.py`:

```python
from lumiagent.tracing.builder_writer import BuilderTraceWriter
```

Add to `__all__`:

```python
"BuilderTraceWriter",
```

- [ ] **Step 4: Run writer tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/tracing/test_builder_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/lumiagent/tracing/__init__.py src/lumiagent/tracing/builder_writer.py tests/tracing/test_builder_writer.py
git commit -m "Add builder-backed trace writer"
```

---

### Task 4: Claude Code Hook Event Schemas and JSONL Reader

**Files:**
- Create: `src/lumiagent/adapters/claude_code/__init__.py`
- Create: `src/lumiagent/adapters/claude_code/events.py`
- Test: `tests/adapters/claude_code/test_events.py`

- [ ] **Step 1: Write failing hook event tests**

Create `tests/adapters/claude_code/test_events.py`:

```python
from pathlib import Path

from lumiagent.adapters.claude_code.events import (
    ClaudeCodeHookEvent,
    read_hook_events,
    write_hook_event,
)


def test_hook_event_defaults_schema_and_source() -> None:
    event = ClaudeCodeHookEvent(
        event_id="evt_1",
        session_id="session_1",
        sequence=1,
        hook_name="PostToolUse",
        tool_name="Read",
        phase="tool_result",
        payload={"status": "success"},
    )

    assert event.schema_version == "coding_hook_event.v1"
    assert event.source == "claude_code_hook"
    assert event.safety == {"redaction_state": "raw"}


def test_write_and_read_hook_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    write_hook_event(
        path,
        ClaudeCodeHookEvent(
            event_id="evt_1",
            session_id="session_1",
            sequence=1,
            hook_name="PreToolUse",
            tool_name="Bash",
            phase="tool_request",
            payload={"arguments": {"command": "python -m pytest -v"}},
        ),
    )

    events = read_hook_events(path)

    assert len(events) == 1
    assert events[0].event_id == "evt_1"
    assert events[0].payload["arguments"]["command"] == "python -m pytest -v"
```

- [ ] **Step 2: Run hook event tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_events.py -v
```

Expected: FAIL because `lumiagent.adapters.claude_code` does not exist.

- [ ] **Step 3: Implement hook event schemas and JSONL helpers**

Create `src/lumiagent/adapters/claude_code/events.py`:

```python
"""Claude Code hook event schemas."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HookPhase = Literal["tool_request", "tool_result", "permission_request", "error"]


class ClaudeCodeHookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "coding_hook_event.v1"
    event_id: str
    session_id: str
    sequence: int
    timestamp: str | None = None
    source: str = "claude_code_hook"
    hook_name: str
    tool_name: str | None = None
    phase: HookPhase
    working_directory: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=lambda: {"redaction_state": "raw"})


def read_hook_events(path: Path) -> list[ClaudeCodeHookEvent]:
    events: list[ClaudeCodeHookEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(ClaudeCodeHookEvent.model_validate_json(line))
    return events


def write_hook_event(path: Path, event: ClaudeCodeHookEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
        handle.write("\n")
```

Create `src/lumiagent/adapters/claude_code/__init__.py`:

```python
"""Claude Code capture adapter."""
from lumiagent.adapters.claude_code.events import (
    ClaudeCodeHookEvent,
    read_hook_events,
    write_hook_event,
)

__all__ = ["ClaudeCodeHookEvent", "read_hook_events", "write_hook_event"]
```

- [ ] **Step 4: Run hook event tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_events.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/lumiagent/adapters/claude_code/__init__.py src/lumiagent/adapters/claude_code/events.py tests/adapters/claude_code/test_events.py
git commit -m "Add Claude Code hook event schema"
```

---

### Task 5: Coding Event Normalizer

**Files:**
- Create: `src/lumiagent/adapters/coding/normalizer.py`
- Modify: `src/lumiagent/adapters/coding/__init__.py`
- Test: `tests/adapters/coding/test_normalizer.py`

- [ ] **Step 1: Write failing normalizer tests**

Create `tests/adapters/coding/test_normalizer.py`:

```python
from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.adapters.coding.normalizer import normalize_hook_event


def _event(tool_name: str, payload: dict[str, object]) -> ClaudeCodeHookEvent:
    return ClaudeCodeHookEvent(
        event_id="evt_1",
        session_id="session_1",
        sequence=1,
        hook_name="PostToolUse",
        tool_name=tool_name,
        phase="tool_result",
        payload=payload,
    )


def test_read_maps_to_file_read() -> None:
    normalized = normalize_hook_event(_event("Read", {"file_path": "src/app.py"}))

    assert normalized.convention == "file_read"
    assert normalized.name == "Read file"
    assert normalized.action_evidence is not None
    assert normalized.action_evidence.tool_name == "Read"


def test_grep_maps_to_file_search() -> None:
    normalized = normalize_hook_event(_event("Grep", {"pattern": "TraceWriter"}))

    assert normalized.convention == "file_search"


def test_edit_maps_to_code_edit() -> None:
    normalized = normalize_hook_event(_event("Edit", {"file_path": "src/app.py"}))

    assert normalized.convention == "code_edit"


def test_pytest_bash_maps_to_test_run() -> None:
    normalized = normalize_hook_event(
        _event(
            "Bash",
            {
                "arguments": {"command": "python -m pytest -v"},
                "exit_code": 0,
                "status": "success",
            },
        )
    )

    assert normalized.convention == "test_run"
    assert normalized.parent_convention == "verification"
    assert normalized.status == "success"


def test_git_diff_maps_to_git_diff() -> None:
    normalized = normalize_hook_event(_event("Bash", {"arguments": {"command": "git diff"}}))

    assert normalized.convention == "git_diff"


def test_unknown_bash_maps_to_shell_command() -> None:
    normalized = normalize_hook_event(_event("Bash", {"arguments": {"command": "pwd"}}))

    assert normalized.convention == "shell_command"
```

- [ ] **Step 2: Run normalizer tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_normalizer.py -v
```

Expected: FAIL because normalizer does not exist.

- [ ] **Step 3: Implement normalizer**

Create `src/lumiagent/adapters/coding/normalizer.py`:

```python
"""Normalize source-specific tool events into Coding Agent events."""
from __future__ import annotations

from typing import Any

from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.adapters.coding.conventions import (
    CODING_CODE_EDIT,
    CODING_FILE_READ,
    CODING_FILE_SEARCH,
    CODING_GIT_DIFF,
    CODING_SHELL_COMMAND,
    CODING_TEST_RUN,
    CODING_VERIFICATION,
)
from lumiagent.adapters.coding.events import CodingActionEvidence, NormalizedCodingEvent


def normalize_hook_event(event: ClaudeCodeHookEvent) -> NormalizedCodingEvent:
    convention, parent, name, reason = _classify(event.tool_name, event.payload)
    status = _status(event.payload)
    evidence = CodingActionEvidence(
        tool_name=event.tool_name,
        arguments=_arguments(event.payload),
        result=_result(event.payload),
        safety=event.safety,
    )
    return NormalizedCodingEvent(
        event_id=f"coding_{event.event_id}",
        source_event_ids=[event.event_id],
        session_id=event.session_id,
        sequence=event.sequence,
        timestamp=event.timestamp,
        convention=convention,
        parent_convention=parent,
        status=status,
        name=name,
        action_evidence=evidence,
        metadata={"classification_reason": reason},
    )


def _classify(
    tool_name: str | None, payload: dict[str, Any]
) -> tuple[str, str | None, str, str]:
    if tool_name in {"Glob", "Grep"}:
        return CODING_FILE_SEARCH, "context_gathering", "Search files", f"{tool_name} maps to file_search"
    if tool_name == "Read":
        return CODING_FILE_READ, "context_gathering", "Read file", "Read maps to file_read"
    if tool_name in {"Edit", "Write", "MultiEdit"}:
        return CODING_CODE_EDIT, None, "Edit code", f"{tool_name} maps to code_edit"
    if tool_name == "Bash":
        command = str(_arguments(payload).get("command", "")).strip().lower()
        if _is_test_command(command):
            return CODING_TEST_RUN, CODING_VERIFICATION, "Run tests", "command matched test pattern"
        if command.startswith("git diff"):
            return CODING_GIT_DIFF, None, "Inspect git diff", "command matched git diff"
        if _is_verification_command(command):
            return CODING_VERIFICATION, None, "Run verification", "command matched verification pattern"
        return CODING_SHELL_COMMAND, None, "Run shell command", "generic Bash command"
    return CODING_SHELL_COMMAND, None, "Use tool", "fallback tool mapping"


def _arguments(payload: dict[str, Any]) -> dict[str, Any]:
    arguments = payload.get("arguments")
    if isinstance(arguments, dict):
        return arguments
    return {key: value for key, value in payload.items() if key not in {"status", "duration_ms"}}


def _result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key in {"status", "exit_code", "duration_ms", "stdout_summary", "stderr_summary", "output_truncated"}
    }


def _status(payload: dict[str, Any]) -> str:
    status = payload.get("status")
    if status in {"success", "error", "running", "unknown"}:
        return str(status)
    if payload.get("exit_code") not in {None, 0}:
        return "error"
    return "unknown"


def _is_test_command(command: str) -> bool:
    return any(
        pattern in command
        for pattern in ("pytest", "npm test", "pnpm test", "yarn test")
    )


def _is_verification_command(command: str) -> bool:
    return any(pattern in command for pattern in ("ruff", "mypy", "pyright", "eslint", "tsc"))
```

Modify `src/lumiagent/adapters/coding/__init__.py`:

```python
from lumiagent.adapters.coding.normalizer import normalize_hook_event
```

Add to `__all__`:

```python
"normalize_hook_event",
```

- [ ] **Step 4: Run normalizer tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_normalizer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/lumiagent/adapters/coding/__init__.py src/lumiagent/adapters/coding/normalizer.py tests/adapters/coding/test_normalizer.py
git commit -m "Add coding event normalizer"
```

---

### Task 6: Minimal Transcript Enrichment

**Files:**
- Create: `src/lumiagent/adapters/claude_code/transcript.py`
- Modify: `src/lumiagent/adapters/claude_code/__init__.py`
- Test: `tests/adapters/claude_code/test_transcript.py`

- [ ] **Step 1: Write failing transcript tests**

Create `tests/adapters/claude_code/test_transcript.py`:

```python
import json
from pathlib import Path

from lumiagent.adapters.claude_code.transcript import enrich_transcript


def test_missing_transcript_returns_unsupported(tmp_path: Path) -> None:
    enrichment = enrich_transcript(tmp_path / "missing.jsonl", session_id="session_1")

    assert enrichment.status == "unsupported"
    assert enrichment.items == []
    assert enrichment.warnings


def test_jsonl_transcript_extracts_user_and_final_response(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "Fix the failing tests."}),
                json.dumps({"role": "assistant", "content": "I will inspect the failure and run pytest."}),
                json.dumps({"role": "assistant", "content": "Fixed the issue and tests pass.", "final": True}),
            ]
        ),
        encoding="utf-8",
    )

    enrichment = enrich_transcript(transcript, session_id="session_1")

    assert enrichment.status == "success"
    assert [item.convention for item in enrichment.items] == [
        "user_prompt",
        "task_understanding",
        "final_response",
    ]
    assert enrichment.items[0].content_summary == "Fix the failing tests."
```

- [ ] **Step 2: Run transcript tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_transcript.py -v
```

Expected: FAIL because transcript module does not exist.

- [ ] **Step 3: Implement minimal transcript enrichment**

Create `src/lumiagent/adapters/claude_code/transcript.py`:

```python
"""Best-effort Claude Code transcript enrichment."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lumiagent.adapters.coding.conventions import (
    CODING_FINAL_RESPONSE,
    CODING_TASK_UNDERSTANDING,
    CODING_USER_PROMPT,
)


class TranscriptSemanticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    timestamp: str | None = None
    convention: str
    role: str
    content_summary: str
    content: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class TranscriptEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "coding_transcript_enrichment.v1"
    session_id: str
    source: str = "claude_code_transcript"
    source_path: str | None = None
    status: Literal["success", "unsupported"]
    items: list[TranscriptSemanticItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def enrich_transcript(path: Path, *, session_id: str) -> TranscriptEnrichment:
    if not path.exists():
        return TranscriptEnrichment(
            session_id=session_id,
            source_path=str(path),
            status="unsupported",
            warnings=["Transcript not found."],
        )
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        return TranscriptEnrichment(
            session_id=session_id,
            source_path=str(path),
            status="unsupported",
            warnings=[f"Transcript could not be parsed: {exc}"],
        )

    items: list[TranscriptSemanticItem] = []
    user_rows = [row for row in rows if row.get("role") == "user" and isinstance(row.get("content"), str)]
    assistant_rows = [
        row for row in rows if row.get("role") == "assistant" and isinstance(row.get("content"), str)
    ]
    if user_rows:
        content = str(user_rows[0]["content"])
        items.append(
            TranscriptSemanticItem(
                item_id="sem_user_prompt_1",
                convention=CODING_USER_PROMPT,
                role="user",
                content_summary=_summary(content),
                content=content,
                confidence="high",
            )
        )
    if assistant_rows:
        first = str(assistant_rows[0]["content"])
        items.append(
            TranscriptSemanticItem(
                item_id="sem_task_understanding_1",
                convention=CODING_TASK_UNDERSTANDING,
                role="assistant",
                content_summary=_summary(first),
                content=first,
                confidence="medium",
            )
        )
        final_row = next((row for row in reversed(assistant_rows) if row.get("final") is True), assistant_rows[-1])
        final = str(final_row["content"])
        if final != first or len(assistant_rows) == 1:
            items.append(
                TranscriptSemanticItem(
                    item_id="sem_final_response_1",
                    convention=CODING_FINAL_RESPONSE,
                    role="assistant",
                    content_summary=_summary(final),
                    content=final,
                    confidence="high",
                )
            )
    return TranscriptEnrichment(
        session_id=session_id,
        source_path=str(path),
        status="success" if items else "unsupported",
        items=items,
        warnings=[] if items else ["No supported transcript messages found."],
    )


def _summary(content: str, *, limit: int = 160) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"
```

Modify `src/lumiagent/adapters/claude_code/__init__.py`:

```python
from lumiagent.adapters.claude_code.transcript import (
    TranscriptEnrichment,
    TranscriptSemanticItem,
    enrich_transcript,
)
```

Add to `__all__`:

```python
"TranscriptEnrichment",
"TranscriptSemanticItem",
"enrich_transcript",
```

- [ ] **Step 4: Run transcript tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_transcript.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

```bash
git add src/lumiagent/adapters/claude_code/__init__.py src/lumiagent/adapters/claude_code/transcript.py tests/adapters/claude_code/test_transcript.py
git commit -m "Add Claude Code transcript enrichment"
```

---

### Task 7: Claude Code Converter

**Files:**
- Create: `src/lumiagent/adapters/claude_code/converter.py`
- Modify: `src/lumiagent/adapters/claude_code/__init__.py`
- Test: `tests/adapters/claude_code/test_converter.py`

- [ ] **Step 1: Write failing converter tests**

Create `tests/adapters/claude_code/test_converter.py`:

```python
from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent


def test_converter_builds_hooks_only_coding_trace() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Read",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_2",
                session_id="session_1",
                sequence=2,
                hook_name="PostToolUse",
                tool_name="Edit",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            ),
            ClaudeCodeHookEvent(
                event_id="evt_3",
                session_id="session_1",
                sequence=3,
                hook_name="PostToolUse",
                tool_name="Bash",
                phase="tool_result",
                payload={"arguments": {"command": "python -m pytest -v"}, "exit_code": 0},
            ),
        ],
    )

    assert run.name == "Claude Code session session_1"
    assert run.metadata["domain"] == "coding_agent"
    root = run.root_spans[0]
    child_types = [child.metadata.get("type") for child in root.children]
    assert "context_gathering" in child_types
    assert "code_edit" in child_types
    assert "verification" in child_types


def test_converter_adds_transcript_semantic_spans() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[],
        semantic_items=[
            {
                "item_id": "sem_1",
                "convention": "user_prompt",
                "role": "user",
                "content_summary": "Fix tests.",
                "content": "Fix tests.",
                "confidence": "high",
            }
        ],
    )

    root = run.root_spans[0]
    assert root.children[0].metadata["type"] == "user_prompt"
    assert root.children[0].artifacts[0].metadata["type"] == "coding_semantic_evidence"
```

- [ ] **Step 2: Run converter tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_converter.py -v
```

Expected: FAIL because converter does not exist.

- [ ] **Step 3: Implement converter**

Create `src/lumiagent/adapters/claude_code/converter.py`:

```python
"""Convert Claude Code events into Coding Agent AgentRun traces."""
from __future__ import annotations

from typing import Any

from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_CONTEXT_GATHERING,
    CODING_DOMAIN,
    CODING_USER_PROMPT,
    CODING_VERIFICATION,
    coding_metadata,
)
from lumiagent.adapters.coding.events import CodingSemanticEvidence
from lumiagent.adapters.coding.normalizer import normalize_hook_event
from lumiagent.tracing import ArtifactKind, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder_writer import BuilderTraceWriter
from lumiagent.tracing.models import AgentRun


class ClaudeCodeTraceConverter:
    def convert(
        self,
        *,
        session_id: str,
        events: list[ClaudeCodeHookEvent],
        semantic_items: list[dict[str, Any]] | None = None,
    ) -> AgentRun:
        writer = BuilderTraceWriter()
        writer.start_run(
            name=f"Claude Code session {session_id}",
            metadata={"domain": CODING_DOMAIN, "source": "claude_code"},
        )
        root_id = writer.start_span(
            "Coding Agent Run",
            kind=SpanKind.CUSTOM,
            metadata=coding_metadata("coding_agent_run", source="claude_code"),
        )
        parent_ids: dict[str, str] = {}
        self._write_semantic_items(writer, root_id, semantic_items or [])
        for event in sorted(events, key=lambda item: item.sequence):
            normalized = normalize_hook_event(event)
            parent_id = root_id
            if normalized.parent_convention == CODING_CONTEXT_GATHERING:
                parent_id = parent_ids.setdefault(
                    CODING_CONTEXT_GATHERING,
                    writer.start_span(
                        "Context Gathering",
                        parent_span_id=root_id,
                        metadata=coding_metadata(CODING_CONTEXT_GATHERING, source="claude_code_hook"),
                    ),
                )
            elif normalized.parent_convention == CODING_VERIFICATION:
                parent_id = parent_ids.setdefault(
                    CODING_VERIFICATION,
                    writer.start_span(
                        "Verification",
                        parent_span_id=root_id,
                        metadata=coding_metadata(CODING_VERIFICATION, source="claude_code_hook"),
                    ),
                )
            span_id = writer.start_span(
                normalized.name,
                kind=SpanKind.TOOL,
                parent_span_id=parent_id,
                input_value=normalized.action_evidence.arguments if normalized.action_evidence else None,
                metadata=coding_metadata(
                    normalized.convention,
                    source="claude_code_hook",
                    source_ids=normalized.source_event_ids,
                    evidence_types=["action_evidence"],
                    classification_reason=str(normalized.metadata.get("classification_reason", "")),
                ),
            )
            if normalized.action_evidence is not None:
                writer.add_artifact(
                    span_id,
                    name="Action Evidence",
                    kind=ArtifactKind.JSON,
                    content=normalized.action_evidence.model_dump(mode="json"),
                    metadata={"type": CODING_ARTIFACT_ACTION_EVIDENCE},
                )
            writer.end_span(
                span_id,
                status=SpanStatus.ERROR if normalized.status == "error" else SpanStatus.SUCCESS,
                output=normalized.action_evidence.result if normalized.action_evidence else None,
            )
        for parent_id in parent_ids.values():
            writer.end_span(parent_id, status=SpanStatus.SUCCESS)
        writer.end_span(root_id, status=SpanStatus.SUCCESS)
        return writer.flush(status=RunStatus.SUCCESS)

    def _write_semantic_items(
        self, writer: BuilderTraceWriter, root_id: str, semantic_items: list[dict[str, Any]]
    ) -> None:
        for item in semantic_items:
            evidence = CodingSemanticEvidence.model_validate(item)
            span_id = writer.start_span(
                _semantic_name(evidence.convention),
                kind=SpanKind.CUSTOM,
                parent_span_id=root_id,
                metadata=coding_metadata(
                    evidence.convention,
                    source="transcript_enrichment",
                    evidence_types=["semantic_evidence"],
                    extra={"source_item_ids": [str(item.get("item_id", ""))], "confidence": evidence.confidence},
                ),
            )
            writer.add_artifact(
                span_id,
                name="Semantic Evidence",
                kind=ArtifactKind.JSON,
                content=evidence.model_dump(mode="json"),
                metadata={"type": CODING_ARTIFACT_SEMANTIC_EVIDENCE},
            )
            writer.end_span(span_id, status=SpanStatus.SUCCESS)


def _semantic_name(convention: str) -> str:
    if convention == CODING_USER_PROMPT:
        return "User Prompt"
    return convention.replace("_", " ").title()
```

Modify `src/lumiagent/adapters/claude_code/__init__.py`:

```python
from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
```

Add to `__all__`:

```python
"ClaudeCodeTraceConverter",
```

- [ ] **Step 4: Run converter tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_converter.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 7**

```bash
git add src/lumiagent/adapters/claude_code/__init__.py src/lumiagent/adapters/claude_code/converter.py tests/adapters/claude_code/test_converter.py
git commit -m "Convert Claude Code events to coding traces"
```

---

### Task 8: Workflow Validator

**Files:**
- Create: `src/lumiagent/adapters/coding/validator.py`
- Modify: `src/lumiagent/adapters/coding/__init__.py`
- Test: `tests/adapters/coding/test_validator.py`

- [ ] **Step 1: Write failing validator tests**

Create `tests/adapters/coding/test_validator.py`:

```python
from lumiagent.adapters.coding.validator import validate_coding_workflow
from lumiagent.tracing import RunStatus, SpanKind, SpanStatus, TraceBuilder


def _run_with_spans(span_types: list[tuple[str, SpanStatus]]):
    builder = TraceBuilder(name="coding run")
    root_id = builder.start_span(
        "Coding Agent Run",
        metadata={"domain": "coding_agent", "type": "coding_agent_run"},
    )
    for span_type, status in span_types:
        span_id = builder.start_span(
            span_type.replace("_", " ").title(),
            kind=SpanKind.TOOL,
            parent_span_id=root_id,
            metadata={"domain": "coding_agent", "type": span_type},
        )
        builder.end_span(span_id, status=status)
    builder.end_span(root_id, status=SpanStatus.SUCCESS)
    return builder.build(status=RunStatus.SUCCESS)


def test_code_edit_without_verification_warns() -> None:
    checks = validate_coding_workflow(_run_with_spans([("code_edit", SpanStatus.SUCCESS)]))

    assert checks.status == "warning"
    assert checks.findings[0].rule_id == "code_edit_requires_verification"
    assert checks.findings[0].severity == "warning"


def test_code_edit_with_test_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([("code_edit", SpanStatus.SUCCESS), ("test_run", SpanStatus.SUCCESS)])
    )

    assert checks.status == "pass"
    assert checks.findings == []


def test_failed_test_without_recovery_errors() -> None:
    checks = validate_coding_workflow(_run_with_spans([("test_run", SpanStatus.ERROR)]))

    assert checks.status == "error"
    assert checks.findings[0].rule_id == "failed_test_requires_recovery"


def test_failed_command_without_recovery_warns() -> None:
    checks = validate_coding_workflow(_run_with_spans([("shell_command", SpanStatus.ERROR)]))

    assert checks.status == "warning"
    assert checks.findings[0].rule_id == "failed_command_requires_recovery"


def test_failed_command_with_recovery_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([
            ("shell_command", SpanStatus.ERROR),
            ("failure_recovery", SpanStatus.SUCCESS),
        ])
    )

    assert checks.status == "pass"


def test_permission_denied_followed_by_risky_action_errors() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([
            ("approval_decision", SpanStatus.ERROR),
            ("shell_command", SpanStatus.SUCCESS),
        ])
    )

    assert checks.status == "error"
    assert checks.findings[0].rule_id == "permission_denied_blocks_action"


def test_final_response_after_unresolved_error_warns() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([
            ("error_observed", SpanStatus.ERROR),
            ("final_response", SpanStatus.SUCCESS),
        ])
    )

    assert checks.status == "warning"
    assert checks.findings[0].rule_id == "final_response_after_unresolved_error"
```

- [ ] **Step 2: Run validator tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_validator.py -v
```

Expected: FAIL because validator does not exist.

- [ ] **Step 3: Implement validator**

Create `src/lumiagent/adapters/coding/validator.py`:

```python
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
from lumiagent.adapters.coding.events import CodingWorkflowChecks, CodingWorkflowFinding
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
                    expected="A failed test_run should be followed by recovery or a passing test_run.",
                    actual="No later recovery action or passing test_run was found.",
                )
            )
    return findings


def _check_failed_command_requires_recovery(spans: list[Span]) -> list[CodingWorkflowFinding]:
    findings: list[CodingWorkflowFinding] = []
    for index, span in enumerate(spans):
        if span.metadata.get("type") != CODING_SHELL_COMMAND or span.status != SpanStatus.ERROR:
            continue
        if _has_later_type(spans, index, {CODING_FAILURE_RECOVERY, CODING_CODE_EDIT, CODING_TEST_RUN, CODING_VERIFICATION}):
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
        later_risky = [item for item in spans[index + 1 :] if item.metadata.get("type") in {CODING_SHELL_COMMAND, CODING_CODE_EDIT}]
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
        has_recovery = any(item.metadata.get("type") in {CODING_FAILURE_RECOVERY, CODING_TEST_RUN, CODING_VERIFICATION} for item in later)
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
                    expected="An observed error should be recovered or verified before final response.",
                    actual="Final response appeared without recovery or verification.",
                )
            )
    return findings


def _has_later_type(spans: list[Span], index: int, span_types: set[str]) -> bool:
    return any(span.metadata.get("type") in span_types for span in spans[index + 1 :])


def _aggregate(findings: list[CodingWorkflowFinding]) -> str:
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
```

Modify `src/lumiagent/adapters/coding/__init__.py`:

```python
from lumiagent.adapters.coding.validator import validate_coding_workflow
```

Add to `__all__`:

```python
"validate_coding_workflow",
```

- [ ] **Step 4: Run validator tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_validator.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 8**

```bash
git add src/lumiagent/adapters/coding/__init__.py src/lumiagent/adapters/coding/validator.py tests/adapters/coding/test_validator.py
git commit -m "Add coding workflow validator"
```

---

### Task 9: Add Workflow Checks to Converter

**Files:**
- Modify: `src/lumiagent/adapters/claude_code/converter.py`
- Test: `tests/adapters/claude_code/test_converter.py`

- [ ] **Step 1: Add failing converter test for workflow check span**

Append to `tests/adapters/claude_code/test_converter.py`:

```python

def test_converter_appends_workflow_check_span() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Edit",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            )
        ],
    )

    root = run.root_spans[0]
    workflow = next(child for child in root.children if child.metadata.get("type") == "workflow_check")
    assert workflow.artifacts[0].metadata["type"] == "coding_workflow_checks"
    assert workflow.artifacts[0].content["status"] == "warning"
```

- [ ] **Step 2: Run converter test and verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_converter.py::test_converter_appends_workflow_check_span -v
```

Expected: FAIL because converter does not append workflow checks.

- [ ] **Step 3: Update converter to append workflow check span**

Modify `src/lumiagent/adapters/claude_code/converter.py` after action spans are written and before final `flush()`.

Add imports:

```python
from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_WORKFLOW_CHECK,
)
from lumiagent.adapters.coding.validator import validate_coding_workflow
```

To keep validation based on the current run, flush once before adding workflow checks is awkward with `TraceBuilder`. Instead, add a private method that creates a temporary run without checks, validates it, then appends checks before final flush. The simplest Phase 3 implementation is to validate after the first flush in converter and then rebuild with checks in a second pass. Replace `convert()` body with this structure:

```python
    def convert(
        self,
        *,
        session_id: str,
        events: list[ClaudeCodeHookEvent],
        semantic_items: list[dict[str, Any]] | None = None,
    ) -> AgentRun:
        run = self._build_run(session_id=session_id, events=events, semantic_items=semantic_items or [], workflow_checks=None)
        checks = validate_coding_workflow(run)
        return self._build_run(
            session_id=session_id,
            events=events,
            semantic_items=semantic_items or [],
            workflow_checks=checks.model_dump(mode="json"),
        )
```

Rename the existing implementation body into `_build_run(...)` and add this at the end before closing the root span:

```python
        if workflow_checks is not None:
            check_id = writer.start_span(
                "Workflow Check",
                kind=SpanKind.CUSTOM,
                parent_span_id=root_id,
                metadata=coding_metadata(
                    CODING_WORKFLOW_CHECK,
                    source="workflow_validator",
                    evidence_types=["workflow_finding"],
                ),
            )
            writer.add_artifact(
                check_id,
                name="Workflow Checks",
                kind=ArtifactKind.JSON,
                content=workflow_checks,
                metadata={"type": CODING_ARTIFACT_WORKFLOW_CHECKS},
            )
            writer.end_span(
                check_id,
                status=SpanStatus.ERROR if workflow_checks["status"] == "error" else SpanStatus.SUCCESS,
            )
```

- [ ] **Step 4: Run converter tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_converter.py tests/adapters/coding/test_validator.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 9**

```bash
git add src/lumiagent/adapters/claude_code/converter.py tests/adapters/claude_code/test_converter.py
git commit -m "Attach workflow checks to coding traces"
```

---

### Task 10: Coding Trace Viewer

**Files:**
- Create: `src/lumiagent/adapters/coding/viewer.py`
- Modify: `src/lumiagent/adapters/coding/__init__.py`
- Test: `tests/adapters/coding/test_viewer.py`

- [ ] **Step 1: Write failing viewer tests**

Create `tests/adapters/coding/test_viewer.py`:

```python
from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.adapters.coding.viewer import render_coding_trace_summary


def test_render_coding_trace_summary_includes_workflow_checks() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="session_1",
        events=[
            ClaudeCodeHookEvent(
                event_id="evt_1",
                session_id="session_1",
                sequence=1,
                hook_name="PostToolUse",
                tool_name="Edit",
                phase="tool_result",
                payload={"file_path": "src/app.py", "status": "success"},
            )
        ],
    )

    lines = render_coding_trace_summary(run, show_checks=True)

    assert "Semantic Summary" in lines
    assert "Workflow Checks" in lines
    assert any("code_edit_requires_verification" in line for line in lines)
```

- [ ] **Step 2: Run viewer test and verify it fails**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_viewer.py -v
```

Expected: FAIL because viewer does not exist.

- [ ] **Step 3: Implement coding viewer**

Create `src/lumiagent/adapters/coding/viewer.py`:

```python
"""Plain-text Coding Agent trace viewer."""
from __future__ import annotations

from typing import Any

from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_DOMAIN,
)
from lumiagent.tracing import AgentRun, Artifact, Span


def is_coding_trace(run: AgentRun) -> bool:
    return run.metadata.get("domain") == CODING_DOMAIN or any(
        span.metadata.get("domain") == CODING_DOMAIN for span in run.root_spans
    )


def render_coding_trace_summary(run: AgentRun, *, show_checks: bool = False) -> list[str]:
    lines = [f"Run: {run.name}", f"Status: {run.status.value}", "", "Semantic Summary"]
    semantic = _semantic_artifacts(run.root_spans)
    if semantic:
        for artifact in semantic[:3]:
            content = _artifact_content(artifact)
            lines.append(f"  {content.get('convention')}: {content.get('content_summary')}")
    else:
        lines.append("  transcript enrichment: unavailable")
    lines.extend(["", "Span Tree"])
    for span in run.root_spans:
        _render_span(lines, span, depth=0)
    checks = _workflow_checks(run.root_spans)
    lines.extend(["", "Workflow Checks"])
    if checks is None:
        lines.append("  status: not_applicable")
    else:
        lines.append(f"  status: {checks.get('status')}")
        if show_checks:
            for finding in checks.get("findings", []):
                lines.append(f"  - rule: {finding.get('rule_id')}")
                lines.append(f"    severity: {finding.get('severity')}")
                lines.append(f"    evidence spans: {', '.join(finding.get('evidence_span_ids', []))}")
    return lines


def _render_span(lines: list[str], span: Span, *, depth: int) -> None:
    indent = "  " * depth
    lines.append(f"{indent}- {span.name} [{span.status.value}]")
    for child in span.children:
        _render_span(lines, child, depth=depth + 1)


def _semantic_artifacts(spans: list[Span]) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for span in spans:
        artifacts.extend(
            artifact
            for artifact in span.artifacts
            if artifact.metadata.get("type") == CODING_ARTIFACT_SEMANTIC_EVIDENCE
        )
        artifacts.extend(_semantic_artifacts(span.children))
    return artifacts


def _workflow_checks(spans: list[Span]) -> dict[str, Any] | None:
    for span in spans:
        for artifact in span.artifacts:
            if artifact.metadata.get("type") == CODING_ARTIFACT_WORKFLOW_CHECKS:
                content = _artifact_content(artifact)
                return content
        found = _workflow_checks(span.children)
        if found is not None:
            return found
    return None


def _artifact_content(artifact: Artifact) -> dict[str, Any]:
    if isinstance(artifact.content, dict):
        return artifact.content
    return {}
```

Modify `src/lumiagent/adapters/coding/__init__.py`:

```python
from lumiagent.adapters.coding.viewer import is_coding_trace, render_coding_trace_summary
```

Add to `__all__`:

```python
"is_coding_trace",
"render_coding_trace_summary",
```

- [ ] **Step 4: Run viewer tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/coding/test_viewer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 10**

```bash
git add src/lumiagent/adapters/coding/__init__.py src/lumiagent/adapters/coding/viewer.py tests/adapters/coding/test_viewer.py
git commit -m "Render coding trace summaries"
```

---

### Task 11: CLI trace and show Integration

**Files:**
- Modify: `src/lumiagent/cli.py`
- Test: `tests/test_cli_coding_trace.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli_coding_trace.py`:

```python
import json
from pathlib import Path

from typer.testing import CliRunner

from lumiagent.cli import app

runner = CliRunner()


def test_trace_command_converts_session_events(tmp_path: Path) -> None:
    session_dir = tmp_path / ".lumiagent" / "sessions" / "session_1"
    session_dir.mkdir(parents=True)
    (session_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "coding_hook_event.v1",
                "event_id": "evt_1",
                "session_id": "session_1",
                "sequence": 1,
                "source": "claude_code_hook",
                "hook_name": "PostToolUse",
                "tool_name": "Edit",
                "phase": "tool_result",
                "payload": {"file_path": "src/app.py", "status": "success"},
                "safety": {"redaction_state": "raw"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "trace.json"

    result = runner.invoke(app, ["trace", "session_1", "-o", str(output), "--sessions-dir", str(tmp_path / ".lumiagent" / "sessions")])

    assert result.exit_code == 0
    assert output.exists()
    assert "Workflow checks: warning" in result.output


def test_show_command_routes_coding_trace(tmp_path: Path) -> None:
    session_dir = tmp_path / ".lumiagent" / "sessions" / "session_1"
    session_dir.mkdir(parents=True)
    (session_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "coding_hook_event.v1",
                "event_id": "evt_1",
                "session_id": "session_1",
                "sequence": 1,
                "source": "claude_code_hook",
                "hook_name": "PostToolUse",
                "tool_name": "Edit",
                "phase": "tool_result",
                "payload": {"file_path": "src/app.py", "status": "success"},
                "safety": {"redaction_state": "raw"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "trace.json"
    runner.invoke(app, ["trace", "session_1", "-o", str(output), "--sessions-dir", str(tmp_path / ".lumiagent" / "sessions")])

    result = runner.invoke(app, ["show", str(output), "--checks"])

    assert result.exit_code == 0
    assert "Semantic Summary" in result.output
    assert "Workflow Checks" in result.output
    assert "code_edit_requires_verification" in result.output
```

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/test_cli_coding_trace.py -v
```

Expected: FAIL because `trace` command and `show --checks` do not exist.

- [ ] **Step 3: Add CLI trace command and show routing**

Modify `src/lumiagent/cli.py`.

Add `checks` option to `show`:

```python
def show(
    trace_path: Annotated[pathlib.Path, typer.Argument(help="Trace JSON file to render.")],
    checks: Annotated[bool, typer.Option("--checks", help="Show workflow check details.")] = False,
) -> None:
```

Replace show body with:

```python
    from lumiagent.adapters.coding.viewer import is_coding_trace, render_coding_trace_summary
    from lumiagent.adapters.mcp.viewer import render_mcp_trace_summary
    from lumiagent.tracing.serializer import from_json

    try:
        run = from_json(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise click.ClickException(f"Invalid trace JSON: {exc}") from exc
    if is_coding_trace(run):
        lines = render_coding_trace_summary(run, show_checks=checks)
    else:
        lines = render_mcp_trace_summary(run)
    for line in lines:
        console.print(line)
```

Add command:

```python
@app.command(name="trace")
def trace_session(
    session_id: Annotated[str, typer.Argument(help="Claude Code session ID to convert.")],
    output: Annotated[pathlib.Path, typer.Option(..., "-o", "--output", help="Trace JSON output path.")],
    sessions_dir: Annotated[
        pathlib.Path,
        typer.Option("--sessions-dir", help="Directory containing LumiAgent session event folders."),
    ] = pathlib.Path(".lumiagent/sessions"),
    transcript_path: Annotated[
        pathlib.Path | None,
        typer.Option("--transcript-path", help="Optional transcript path for semantic enrichment."),
    ] = None,
) -> None:
    from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
    from lumiagent.adapters.claude_code.events import read_hook_events
    from lumiagent.adapters.claude_code.transcript import enrich_transcript
    from lumiagent.adapters.coding.viewer import render_coding_trace_summary
    from lumiagent.tracing.serializer import to_json

    events_path = sessions_dir / session_id / "events.jsonl"
    if not events_path.exists():
        raise click.ClickException(f"Session events not found: {events_path}")
    events = read_hook_events(events_path)
    semantic_items = None
    enrichment_status = "unavailable"
    if transcript_path is not None:
        enrichment = enrich_transcript(transcript_path, session_id=session_id)
        semantic_items = [item.model_dump(mode="json") for item in enrichment.items]
        enrichment_status = enrichment.status
    run = ClaudeCodeTraceConverter().convert(
        session_id=session_id,
        events=events,
        semantic_items=semantic_items,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(to_json(run), encoding="utf-8")
    summary = render_coding_trace_summary(run)
    workflow_status = next(
        (line.strip().removeprefix("status: ") for line in summary if line.strip().startswith("status: ")),
        "not_applicable",
    )
    console.print(f"Trace written: {output}")
    console.print(f"Workflow checks: {workflow_status}")
    console.print(f"Transcript enrichment: {enrichment_status}")
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/test_cli_coding_trace.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 11**

```bash
git add src/lumiagent/cli.py tests/test_cli_coding_trace.py
git commit -m "Add coding trace CLI commands"
```

---

### Task 12: Claude Code Setup and Hook Helpers

**Files:**
- Create: `src/lumiagent/adapters/claude_code/setup.py`
- Create: `src/lumiagent/adapters/claude_code/hooks.py`
- Modify: `src/lumiagent/adapters/claude_code/__init__.py`
- Modify: `src/lumiagent/cli.py`
- Test: `tests/adapters/claude_code/test_setup.py`

- [ ] **Step 1: Write failing setup tests**

Create `tests/adapters/claude_code/test_setup.py`:

```python
import json
from pathlib import Path

from lumiagent.adapters.claude_code.setup import configure_claude_code_hooks


def test_configure_claude_code_hooks_creates_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"

    result = configure_claude_code_hooks(settings_path)

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert result.updated is True
    assert "hooks" in data
    assert "PostToolUse" in data["hooks"]


def test_configure_claude_code_hooks_preserves_existing_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(git status:*)"]}, "hooks": {"Stop": []}}),
        encoding="utf-8",
    )

    configure_claude_code_hooks(settings_path)

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["permissions"] == {"allow": ["Bash(git status:*)"]}
    assert "Stop" in data["hooks"]
    assert "PostToolUse" in data["hooks"]
```

- [ ] **Step 2: Run setup tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_setup.py -v
```

Expected: FAIL because setup module does not exist.

- [ ] **Step 3: Implement setup helper and hook entrypoint**

Create `src/lumiagent/adapters/claude_code/setup.py`:

```python
"""Claude Code hook setup helpers."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class ClaudeCodeSetupResult(BaseModel):
    settings_path: Path
    updated: bool
    configured_hooks: list[str]


def configure_claude_code_hooks(settings_path: Path) -> ClaudeCodeSetupResult:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        data = {}
    hooks = data.setdefault("hooks", {})
    configured: list[str] = []
    command = "python -m lumiagent.adapters.claude_code.hooks"
    for hook_name in ("PreToolUse", "PostToolUse"):
        entries = hooks.setdefault(hook_name, [])
        entry = {"matcher": "*", "hooks": [{"type": "command", "command": command}]}
        if entry not in entries:
            entries.append(entry)
            configured.append(hook_name)
    settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return ClaudeCodeSetupResult(
        settings_path=settings_path,
        updated=bool(configured),
        configured_hooks=configured,
    )
```

Create `src/lumiagent/adapters/claude_code/hooks.py`:

```python
"""Claude Code hook entrypoint.

The implementation is intentionally minimal in Phase 3. The hook command accepts
JSON from stdin when Claude Code provides it and appends a LumiAgent-owned event
record to the configured session events file.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent, write_hook_event


def main() -> None:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    session_id = str(payload.get("session_id") or os.environ.get("LUMIAGENT_SESSION_ID") or "default")
    sequence = int(payload.get("sequence") or 1)
    event = ClaudeCodeHookEvent(
        event_id=str(payload.get("event_id") or f"evt_{sequence}"),
        session_id=session_id,
        sequence=sequence,
        timestamp=payload.get("timestamp"),
        hook_name=str(payload.get("hook_name") or payload.get("hook_event_name") or "unknown"),
        tool_name=payload.get("tool_name"),
        phase=str(payload.get("phase") or "tool_result"),
        working_directory=payload.get("cwd"),
        payload=payload,
    )
    write_hook_event(Path(".lumiagent") / "sessions" / session_id / "events.jsonl", event)


if __name__ == "__main__":
    main()
```

Modify `src/lumiagent/adapters/claude_code/__init__.py`:

```python
from lumiagent.adapters.claude_code.setup import ClaudeCodeSetupResult, configure_claude_code_hooks
```

Add to `__all__`:

```python
"ClaudeCodeSetupResult",
"configure_claude_code_hooks",
```

- [ ] **Step 4: Add CLI setup command**

Modify `src/lumiagent/cli.py` by adding a setup typer near `capture_app`:

```python
setup_app = typer.Typer(help="Configure integrations.")
app.add_typer(setup_app, name="setup")
```

Add command:

```python
@setup_app.command(name="claude-code")
def setup_claude_code(
    settings_path: Annotated[
        pathlib.Path,
        typer.Option("--settings-path", help="Claude Code settings path to update."),
    ] = pathlib.Path(".claude/settings.json"),
) -> None:
    from lumiagent.adapters.claude_code.setup import configure_claude_code_hooks

    result = configure_claude_code_hooks(settings_path)
    console.print(f"Claude Code settings: {result.settings_path}")
    console.print(f"Updated: {result.updated}")
    console.print(f"Configured hooks: {', '.join(result.configured_hooks) or 'already configured'}")
```

- [ ] **Step 5: Run setup tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_setup.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 12**

```bash
git add src/lumiagent/adapters/claude_code/__init__.py src/lumiagent/adapters/claude_code/hooks.py src/lumiagent/adapters/claude_code/setup.py src/lumiagent/cli.py tests/adapters/claude_code/test_setup.py
git commit -m "Add Claude Code hook setup"
```

---

### Task 13: Sanitizer and Fixtures

**Files:**
- Create: `src/lumiagent/adapters/claude_code/sanitizer.py`
- Create: `tests/adapters/claude_code/test_sanitizer.py`
- Create fixtures under `tests/adapters/coding/fixtures/` and `tests/adapters/claude_code/fixtures/`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing sanitizer tests**

Create `tests/adapters/claude_code/test_sanitizer.py`:

```python
from lumiagent.adapters.claude_code.sanitizer import sanitize_value


def test_sanitize_value_replaces_project_paths() -> None:
    value = {
        "working_directory": "D:/Projects/github/lumiagent",
        "payload": {"file_path": "D:/Projects/github/lumiagent/src/app.py"},
    }

    sanitized = sanitize_value(value, project_root="D:/Projects/github/lumiagent")

    assert sanitized["working_directory"] == "<PROJECT_DIR>"
    assert sanitized["payload"]["file_path"] == "<PROJECT_DIR>/src/app.py"


def test_sanitize_value_redacts_token_like_keys() -> None:
    sanitized = sanitize_value({"api_key": "secret", "nested": {"token": "abc"}})

    assert sanitized == {"api_key": "<REDACTED>", "nested": {"token": "<REDACTED>"}}
```

- [ ] **Step 2: Run sanitizer tests and verify they fail**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_sanitizer.py -v
```

Expected: FAIL because sanitizer does not exist.

- [ ] **Step 3: Implement sanitizer**

Create `src/lumiagent/adapters/claude_code/sanitizer.py`:

```python
"""Sanitization helpers for real Claude Code fixtures."""
from __future__ import annotations

from typing import Any

_SECRET_KEYS = {"api_key", "apikey", "token", "access_token", "secret", "password", "credential"}


def sanitize_value(value: Any, *, project_root: str | None = None) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SECRET_KEYS:
                sanitized[key] = "<REDACTED>"
            else:
                sanitized[key] = sanitize_value(item, project_root=project_root)
        return sanitized
    if isinstance(value, list):
        return [sanitize_value(item, project_root=project_root) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if project_root:
            root = project_root.replace("\\", "/")
            normalized = normalized.replace(root, "<PROJECT_DIR>")
        return normalized
    return value
```

- [ ] **Step 4: Generate committed synthetic fixtures**

Use a short Python script in a temporary shell command to create fixtures from converter output. Run:

```powershell
$env:PYTHONPATH = "src"; python - <<'PY'
import json
from pathlib import Path
from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.tracing.serializer import to_json

fixtures = Path('tests/adapters/coding/fixtures')
fixtures.mkdir(parents=True, exist_ok=True)

def event(event_id, sequence, tool_name, payload):
    return ClaudeCodeHookEvent(
        event_id=event_id,
        session_id='fixture_session',
        sequence=sequence,
        hook_name='PostToolUse',
        tool_name=tool_name,
        phase='tool_result',
        payload=payload,
    )

cases = {
    'coding_trace_success.json': [
        event('evt_1', 1, 'Read', {'file_path': '<PROJECT_DIR>/src/app.py', 'status': 'success'}),
        event('evt_2', 2, 'Edit', {'file_path': '<PROJECT_DIR>/src/app.py', 'status': 'success'}),
        event('evt_3', 3, 'Bash', {'arguments': {'command': 'python -m pytest -v'}, 'exit_code': 0, 'status': 'success'}),
    ],
    'coding_trace_missing_verification.json': [
        event('evt_1', 1, 'Edit', {'file_path': '<PROJECT_DIR>/src/app.py', 'status': 'success'}),
    ],
    'coding_trace_failed_test_recovered.json': [
        event('evt_1', 1, 'Edit', {'file_path': '<PROJECT_DIR>/src/app.py', 'status': 'success'}),
        event('evt_2', 2, 'Bash', {'arguments': {'command': 'python -m pytest -v'}, 'exit_code': 1, 'status': 'error'}),
        event('evt_3', 3, 'Edit', {'file_path': '<PROJECT_DIR>/src/app.py', 'status': 'success'}),
        event('evt_4', 4, 'Bash', {'arguments': {'command': 'python -m pytest -v'}, 'exit_code': 0, 'status': 'success'}),
    ],
    'coding_trace_permission_denied.json': [
        event('evt_1', 1, 'Bash', {'arguments': {'command': 'git reset --hard'}, 'status': 'error'}),
    ],
}
converter = ClaudeCodeTraceConverter()
for name, events in cases.items():
    run = converter.convert(session_id='fixture_session', events=events)
    (fixtures / name).write_text(to_json(run), encoding='utf-8')

real_dir = Path('tests/adapters/claude_code/fixtures')
real_dir.mkdir(parents=True, exist_ok=True)
real_run = converter.convert(
    session_id='real_session_sanitized',
    events=cases['coding_trace_success.json'],
    semantic_items=[{
        'item_id': 'sem_1',
        'convention': 'user_prompt',
        'role': 'user',
        'content_summary': 'Fix a small failing test in a sanitized fixture project.',
        'content': None,
        'confidence': 'high',
    }],
)
(real_dir / 'real_session_sanitized_trace.json').write_text(to_json(real_run), encoding='utf-8')
PY
```

Expected: fixture files are created.

- [ ] **Step 5: Update `.gitignore` for raw local capture**

Add to `.gitignore` if not already present:

```gitignore
.lumiagent/sessions/
.lumiagent/traces/*-raw.json
```

- [ ] **Step 6: Run sanitizer and fixture validation tests**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/adapters/claude_code/test_sanitizer.py tests/adapters/coding/test_validator.py tests/adapters/coding/test_viewer.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 13**

```bash
git add .gitignore src/lumiagent/adapters/claude_code/sanitizer.py tests/adapters/claude_code/test_sanitizer.py tests/adapters/coding/fixtures tests/adapters/claude_code/fixtures
git commit -m "Add sanitized coding trace fixtures"
```

---

### Task 14: Technical Report

**Files:**
- Create: `docs/reports/coding-agent-trace-model-technical-report.zh-CN.md`

- [ ] **Step 1: Write technical report before final verification**

Create `docs/reports/coding-agent-trace-model-technical-report.zh-CN.md`:

```markdown
# Coding Agent Trace Model 技术报告

## 背景与目标

Phase 3 建立框架无关的完整语义 Coding Agent Trace Model，并以 Claude Code hooks 与最小 transcript enrichment 作为首个真实采集适配路径。目标是证明 Coding Agent 从用户需求、任务理解、上下文收集、工具动作、代码修改、验证、失败恢复、结果解释到最终回复的过程可以被结构化采集、转换、预检和查看。

## 需求范围

本阶段实现：

- Coding Agent trace conventions。
- action evidence 与 semantic evidence。
- BuilderTraceWriter。
- Claude Code hook event schema、JSONL reader、setup helper 和 converter。
- best-effort transcript enrichment。
- deterministic workflow validator。
- Coding Agent trace CLI show 输出。
- synthetic fixtures 与 sanitized real fixture。

本阶段不实现：

- Phase 4 Evaluation / Diagnosis Engine。
- LLM-based diagnosis、score、复杂 suggested fix。
- 完整 Claude Code 内部 transcript 解析。
- Phase 2b McpTraceMapper 迁移。
- Web UI、TUI、Replay ViewModel、SDK decorator、MCP proxy、生产级 writer。

## 架构设计

核心链路：

```text
Claude Code hooks events + optional transcript enrichment
  -> normalized Coding Agent events
  -> TraceWriter
  -> AgentRun
  -> WorkflowValidator
  -> CLI trace review
```

Coding Agent 通用语义位于 `src/lumiagent/adapters/coding/`。Claude Code 特定采集位于 `src/lumiagent/adapters/claude_code/`。TraceWriter 的最小实现位于 `src/lumiagent/tracing/builder_writer.py`，内部复用既有 TraceBuilder。

## 技术选择

- 使用 Pydantic 表达事件、证据和 workflow finding schema。
- 使用 metadata/artifact 承载 Coding Agent 语义，避免污染 Trace Core。
- 使用 TraceWriter 处理增量 hooks capture，不强制改造 MCP batch mapper。
- transcript enrichment 采用 best-effort 策略，避免依赖不稳定内部格式。
- workflow validator 只做确定性、高信心规则，不替代 Evaluation / Diagnosis。

## 实现要点

- Coding Agent conventions 按语义动作建模，而不是按 Claude Code tool 名称建模。
- normalizer 将 Read/Grep/Edit/Bash 等工具事件映射为 file_read、file_search、code_edit、test_run、verification、git_diff 或 shell_command。
- converter 保留 source event IDs，便于从 AgentRun 回溯到原始 hook events。
- workflow_check span 通过 artifact 保存结构化检查结果。
- sanitized fixtures 保留结构和 evidence shape，但移除敏感路径、私有内容和凭据。

## 验证计划

最终验证将在实现完成后运行以下命令，并在本报告中记录实际结果：

```powershell
$env:PYTHONPATH = "src"; python -m pytest -v
$env:PYTHONPATH = "src"; python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture tests/tracing tests/adapters tests/capture tests/test_cli_coding_trace.py
$env:PYTHONPATH = "src"; python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture
```

真实 Claude Code capture 验证将在本地执行，raw 数据仅保留在 `.lumiagent/` 下，远程只提交 sanitized fixture。

## 验证结果

待最终验证阶段更新。本节在 Task 15 中必须替换为实际命令、退出码和结果摘要，不能保留为占位状态。

## 风险与权衡

- Claude Code hook payload 可能随版本变化；实现采用可用字段和 graceful degradation。
- transcript enrichment 不稳定；hooks-only trace 是最低可靠闭环。
- 真实 trace 可能包含敏感数据；raw 数据只本地保存，远程只提交 sanitized fixture。
- workflow validator 可能误报；因此仅定位为 Workflow Checks，不输出最终诊断。
- setup claude-code 会修改 `.claude/settings.json`；实现应保留已有 hooks 和设置。

## 后续建议

- Phase 4 Diagnosis Agent 消费 workflow checks 作为 deterministic pre-check evidence。
- Phase 5 Replay / Visualization 使用本阶段的 semantic summary 和 workflow_check artifact 构建 view model。
- 后续可评估是否将更多 capture strategy 接入 TraceWriter，但不强制迁移 MCP batch mapper。
```

- [ ] **Step 2: Commit Task 14**

```bash
git add docs/reports/coding-agent-trace-model-technical-report.zh-CN.md
git commit -m "Document coding trace model implementation"
```

---

### Task 15: Full Verification

**Files:**
- No source files unless verification reveals fixes are needed.

- [ ] **Step 1: Run full pytest**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run ruff**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture tests/tracing tests/adapters tests/capture tests/test_cli_coding_trace.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Run mypy**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture
```

Expected: `Success: no issues found`.

- [ ] **Step 4: Run CLI smoke test using synthetic session**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli trace session_1 --sessions-dir tests/adapters/claude_code/fixtures -o .lumiagent/traces/session_1-raw.json
```

If no fixture session directory exists, create a small local `.lumiagent/sessions/session_1/events.jsonl` with a sanitized event and run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli trace session_1 -o .lumiagent/traces/session_1-raw.json
```

Expected: trace written and workflow checks printed.

- [ ] **Step 5: Run CLI show smoke test**

Run:

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli show .lumiagent/traces/session_1-raw.json --checks
```

Expected: output includes `Semantic Summary`, `Span Tree`, and `Workflow Checks`.

- [ ] **Step 6: Update technical report verification section**

Modify `docs/reports/coding-agent-trace-model-technical-report.zh-CN.md` and replace the pending verification section with actual command results.

- [ ] **Step 7: Commit verification report update**

```bash
git add docs/reports/coding-agent-trace-model-technical-report.zh-CN.md
git commit -m "Record coding trace verification results"
```

---

## Self-Review

### Spec coverage

- Coding Agent conventions: Tasks 1-2.
- TraceWriter: Task 3.
- Claude Code hooks events/setup: Tasks 4 and 12.
- Transcript enrichment: Task 6.
- Normalization and converter: Tasks 5, 7, 9.
- Workflow validator: Task 8.
- CLI show and checks: Tasks 10-11.
- Fixtures and sanitization: Task 13.
- Technical report: Task 14.
- Verification: Task 15.

### Plan quality scan

No `TBD`, `TODO`, `implement later`, or unspecified test steps remain. The technical report intentionally starts with a pending verification section that Task 15 replaces with actual command results after verification commands run.

### Type consistency

The plan consistently uses:

- `BuilderTraceWriter`
- `ClaudeCodeHookEvent`
- `ClaudeCodeTraceConverter`
- `CodingActionEvidence`
- `CodingSemanticEvidence`
- `CodingWorkflowFinding`
- `CodingWorkflowChecks`
- `NormalizedCodingEvent`
- `validate_coding_workflow`
- `render_coding_trace_summary`

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-29-coding-agent-trace-model.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.

2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
