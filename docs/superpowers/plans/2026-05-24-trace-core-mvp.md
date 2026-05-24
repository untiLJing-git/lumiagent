# Trace Core MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build LumiAgent's first-version Agent Trace / Eval Core: a framework-agnostic Span Tree data model with serialization, validation, sample traces, and tests.

**Architecture:** Add an independent `lumiagent.tracing` package that depends only on Pydantic and the Python standard library. The package is split into enums, models, serializer, validator, and builder so future MCP/Coding Agent adapters can build traces without coupling the core to LLM, tool, RAG, platform, FastAPI, ChromaDB, or MCP SDK modules.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, standard-library `datetime`, `uuid`, `json`, and `pathlib`.

---

## File Structure

Create these files:

- `src/lumiagent/tracing/__init__.py` — public exports for the tracing package.
- `src/lumiagent/tracing/enums.py` — string enums for run/span/event/artifact/target/severity values.
- `src/lumiagent/tracing/models.py` — Pydantic models for `AgentRun`, `Span`, `Event`, `Artifact`, `Evaluation`, and `Diagnosis`.
- `src/lumiagent/tracing/serializer.py` — JSON/dict round-trip helpers.
- `src/lumiagent/tracing/validator.py` — structural validation with a custom `TraceValidationError`.
- `src/lumiagent/tracing/builder.py` — minimal ergonomic `TraceBuilder` for constructing traces.
- `tests/tracing/test_models.py` — model creation and field behavior tests.
- `tests/tracing/test_serializer.py` — JSON round-trip tests.
- `tests/tracing/test_validator.py` — valid and invalid trace validation tests.
- `tests/tracing/test_builder.py` — builder workflow tests.
- `tests/tracing/fixtures/generic_agent_run.json` — generic Agent trace fixture.
- `tests/tracing/fixtures/coding_agent_trace_sample.json` — Coding Agent workflow fixture using generic/custom span kinds and metadata.

Do not modify existing runtime modules in this MVP unless import/export wiring requires it.

---

### Task 1: Define tracing enums and data models

**Files:**
- Create: `src/lumiagent/tracing/enums.py`
- Create: `src/lumiagent/tracing/models.py`
- Create: `src/lumiagent/tracing/__init__.py`
- Test: `tests/tracing/test_models.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/tracing/test_models.py`:

```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from lumiagent.tracing import (
    AgentRun,
    Artifact,
    ArtifactKind,
    Diagnosis,
    Event,
    EventLevel,
    Evaluation,
    RunStatus,
    Severity,
    Span,
    SpanKind,
    SpanStatus,
    TargetType,
)


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def test_create_agent_run_with_nested_span() -> None:
    child = Span(
        run_id="run_1",
        span_id="span_llm",
        parent_span_id="span_agent",
        name="Call model",
        kind=SpanKind.LLM,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        input={"messages": ["hello"]},
        output={"text": "world"},
    )
    root = Span(
        run_id="run_1",
        span_id="span_agent",
        parent_span_id=None,
        name="Agent workflow",
        kind=SpanKind.AGENT,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        children=[child],
    )
    run = AgentRun(
        run_id="run_1",
        name="demo run",
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[root],
    )

    assert run.run_id == "run_1"
    assert run.root_spans[0].children[0].kind is SpanKind.LLM
    assert run.root_spans[0].children[0].input == {"messages": ["hello"]}


def test_event_artifact_evaluation_and_diagnosis_models() -> None:
    event = Event(
        event_id="event_1",
        name="fallback_triggered",
        timestamp=utc_now(),
        level=EventLevel.WARNING,
        message="Primary provider failed.",
    )
    artifact = Artifact(
        artifact_id="artifact_1",
        name="prompt",
        kind=ArtifactKind.PROMPT,
        content="Hello",
    )
    evaluation = Evaluation(
        evaluation_id="eval_1",
        target_type=TargetType.RUN,
        target_id="run_1",
        name="quality",
        score=0.8,
        label="pass",
        reason="The answer is grounded.",
        evidence_span_ids=["span_llm"],
    )
    diagnosis = Diagnosis(
        diagnosis_id="diag_1",
        target_type=TargetType.RUN,
        target_id="run_1",
        failure_type="insufficient_verification",
        severity=Severity.MEDIUM,
        summary="The agent changed code without running tests.",
        evidence_span_ids=["span_edit"],
        suggested_fix="Run the relevant test command before finishing.",
    )

    assert event.level is EventLevel.WARNING
    assert artifact.kind is ArtifactKind.PROMPT
    assert evaluation.score == 0.8
    assert diagnosis.severity is Severity.MEDIUM


def test_score_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        Evaluation(
            evaluation_id="eval_bad",
            target_type=TargetType.RUN,
            target_id="run_1",
            name="quality",
            score=1.5,
            reason="Invalid score.",
        )


def test_artifact_requires_content_or_uri() -> None:
    with pytest.raises(ValidationError):
        Artifact(
            artifact_id="artifact_bad",
            name="empty",
            kind=ArtifactKind.CUSTOM,
        )


def test_ended_at_cannot_precede_started_at() -> None:
    with pytest.raises(ValidationError):
        Span(
            run_id="run_1",
            span_id="span_bad",
            name="Bad timing",
            kind=SpanKind.CUSTOM,
            status=SpanStatus.ERROR,
            started_at=datetime(2026, 5, 24, 12, 1, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
```

- [ ] **Step 2: Run model tests to verify they fail**

Run:

```bash
pytest tests/tracing/test_models.py -v
```

Expected: FAIL because `lumiagent.tracing` does not exist.

- [ ] **Step 3: Implement enums**

Create `src/lumiagent/tracing/enums.py`:

```python
"""Enums for LumiAgent trace models."""
from __future__ import annotations

from enum import Enum


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class SpanKind(str, Enum):
    AGENT = "agent"
    LLM = "llm"
    TOOL = "tool"
    RAG = "rag"
    MEMORY = "memory"
    EVALUATOR = "evaluator"
    FALLBACK = "fallback"
    ERROR = "error"
    CUSTOM = "custom"


class EventLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ArtifactKind(str, Enum):
    PROMPT = "prompt"
    COMPLETION = "completion"
    RETRIEVED_CHUNKS = "retrieved_chunks"
    TOOL_RESULT = "tool_result"
    CODE_DIFF = "code_diff"
    TEST_OUTPUT = "test_output"
    LOG = "log"
    CUSTOM = "custom"


class TargetType(str, Enum):
    RUN = "run"
    SPAN = "span"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

- [ ] **Step 4: Implement Pydantic models**

Create `src/lumiagent/tracing/models.py`:

```python
"""Pydantic models for Agent trace data."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    ArtifactKind,
    EventLevel,
    RunStatus,
    Severity,
    SpanKind,
    SpanStatus,
    TargetType,
)

TraceValue = dict[str, Any] | list[Any] | str | int | float | bool | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class TimeRangeModel(BaseModel):
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_time_range(self) -> TimeRangeModel:
        if self.ended_at is not None and self.started_at > self.ended_at:
            raise ValueError("started_at must be before or equal to ended_at")
        return self


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("event"))
    name: str
    timestamp: datetime = Field(default_factory=utc_now)
    level: EventLevel = EventLevel.INFO
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class Artifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: new_id("artifact"))
    name: str
    kind: ArtifactKind = ArtifactKind.CUSTOM
    uri: Optional[str] = None
    content: TraceValue = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def require_content_or_uri(self) -> Artifact:
        if self.uri is None and self.content is None:
            raise ValueError("artifact requires content or uri")
        return self


class Span(TimeRangeModel):
    span_id: str = Field(default_factory=lambda: new_id("span"))
    run_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: SpanKind = SpanKind.CUSTOM
    status: SpanStatus = SpanStatus.PENDING
    input: TraceValue = None
    output: TraceValue = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    children: list[Span] = Field(default_factory=list)

    @field_validator("span_id", "run_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class Evaluation(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: new_id("eval"))
    target_type: TargetType
    target_id: str
    name: str
    score: Optional[float] = None
    label: Optional[str] = None
    reason: str = ""
    evidence_span_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evaluation_id", "target_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")
        return value


class Diagnosis(BaseModel):
    diagnosis_id: str = Field(default_factory=lambda: new_id("diag"))
    target_type: TargetType
    target_id: str
    failure_type: str
    severity: Severity = Severity.MEDIUM
    summary: str
    evidence_span_ids: list[str] = Field(default_factory=list)
    suggested_fix: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("diagnosis_id", "target_id", "failure_type", "summary", "suggested_fix")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class AgentRun(TimeRangeModel):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    name: str
    status: RunStatus = RunStatus.PENDING
    input: TraceValue = None
    output: TraceValue = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    root_spans: list[Span] = Field(default_factory=list)
    evaluations: list[Evaluation] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)

    @field_validator("run_id", "name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value
```

- [ ] **Step 5: Export tracing API**

Create `src/lumiagent/tracing/__init__.py`:

```python
"""Trace / Eval Core public API."""
from lumiagent.tracing.enums import (
    ArtifactKind,
    EventLevel,
    RunStatus,
    Severity,
    SpanKind,
    SpanStatus,
    TargetType,
)
from lumiagent.tracing.models import AgentRun, Artifact, Diagnosis, Event, Evaluation, Span

__all__ = [
    "AgentRun",
    "Artifact",
    "ArtifactKind",
    "Diagnosis",
    "Event",
    "EventLevel",
    "Evaluation",
    "RunStatus",
    "Severity",
    "Span",
    "SpanKind",
    "SpanStatus",
    "TargetType",
]
```

- [ ] **Step 6: Run model tests**

Run:

```bash
pytest tests/tracing/test_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/lumiagent/tracing/__init__.py src/lumiagent/tracing/enums.py src/lumiagent/tracing/models.py tests/tracing/test_models.py
git commit -m "Add trace core data models"
```

---

### Task 2: Add JSON serializer round-trip support

**Files:**
- Create: `src/lumiagent/tracing/serializer.py`
- Modify: `src/lumiagent/tracing/__init__.py`
- Test: `tests/tracing/test_serializer.py`

- [ ] **Step 1: Write failing serializer tests**

Create `tests/tracing/test_serializer.py`:

```python
from datetime import datetime, timezone

from lumiagent.tracing import AgentRun, RunStatus, Span, SpanKind, SpanStatus
from lumiagent.tracing.serializer import from_dict, from_json, to_dict, to_json


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def make_run() -> AgentRun:
    root = Span(
        run_id="run_serialize",
        span_id="span_agent",
        name="Agent",
        kind=SpanKind.AGENT,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
    )
    return AgentRun(
        run_id="run_serialize",
        name="serialize demo",
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[root],
    )


def test_to_dict_uses_string_enums_and_iso_datetimes() -> None:
    data = to_dict(make_run())

    assert data["status"] == "success"
    assert data["started_at"] == "2026-05-24T12:00:00Z"
    assert data["root_spans"][0]["kind"] == "agent"


def test_json_round_trip_preserves_semantics() -> None:
    original = make_run()
    encoded = to_json(original)
    decoded = from_json(encoded)

    assert decoded.run_id == original.run_id
    assert decoded.status is RunStatus.SUCCESS
    assert decoded.root_spans[0].kind is SpanKind.AGENT
    assert decoded.root_spans[0].started_at == original.root_spans[0].started_at


def test_from_dict_loads_agent_run() -> None:
    data = to_dict(make_run())
    decoded = from_dict(data)

    assert decoded.name == "serialize demo"
    assert decoded.root_spans[0].span_id == "span_agent"
```

- [ ] **Step 2: Run serializer tests to verify they fail**

Run:

```bash
pytest tests/tracing/test_serializer.py -v
```

Expected: FAIL because `serializer.py` does not exist.

- [ ] **Step 3: Implement serializer helpers**

Create `src/lumiagent/tracing/serializer.py`:

```python
"""Serialization helpers for Agent traces."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .models import AgentRun


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value.astimezone(timezone.utc)
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def to_dict(run: AgentRun) -> dict[str, Any]:
    return _to_jsonable(run.model_dump(mode="json"))


def to_json(run: AgentRun, *, indent: int = 2) -> str:
    return json.dumps(to_dict(run), ensure_ascii=False, indent=indent)


def from_dict(data: dict[str, Any]) -> AgentRun:
    return AgentRun.model_validate(data)


def from_json(data: str) -> AgentRun:
    return from_dict(json.loads(data))
```

- [ ] **Step 4: Export serializer functions**

Modify `src/lumiagent/tracing/__init__.py` to include:

```python
from lumiagent.tracing.serializer import from_dict, from_json, to_dict, to_json
```

Update `__all__` with:

```python
"from_dict",
"from_json",
"to_dict",
"to_json",
```

- [ ] **Step 5: Run serializer tests**

Run:

```bash
pytest tests/tracing/test_serializer.py -v
```

Expected: PASS.

- [ ] **Step 6: Run model and serializer tests**

Run:

```bash
pytest tests/tracing/test_models.py tests/tracing/test_serializer.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/lumiagent/tracing/__init__.py src/lumiagent/tracing/serializer.py tests/tracing/test_serializer.py
git commit -m "Add trace JSON serialization"
```

---

### Task 3: Add structural trace validator

**Files:**
- Create: `src/lumiagent/tracing/validator.py`
- Modify: `src/lumiagent/tracing/__init__.py`
- Test: `tests/tracing/test_validator.py`

- [ ] **Step 1: Write failing validator tests**

Create `tests/tracing/test_validator.py`:

```python
from datetime import datetime, timezone

import pytest

from lumiagent.tracing import (
    AgentRun,
    Artifact,
    ArtifactKind,
    Diagnosis,
    Evaluation,
    RunStatus,
    Severity,
    Span,
    SpanKind,
    SpanStatus,
    TargetType,
)
from lumiagent.tracing.validator import TraceValidationError, validate_run


def utc_now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def valid_run() -> AgentRun:
    llm = Span(
        run_id="run_valid",
        span_id="span_llm",
        parent_span_id="span_agent",
        name="LLM",
        kind=SpanKind.LLM,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        artifacts=[Artifact(artifact_id="artifact_prompt", name="prompt", kind=ArtifactKind.PROMPT, content="Hi")],
    )
    agent = Span(
        run_id="run_valid",
        span_id="span_agent",
        name="Agent",
        kind=SpanKind.AGENT,
        status=SpanStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        children=[llm],
    )
    return AgentRun(
        run_id="run_valid",
        name="valid run",
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[agent],
        evaluations=[
            Evaluation(
                evaluation_id="eval_valid",
                target_type=TargetType.RUN,
                target_id="run_valid",
                name="quality",
                score=1.0,
                reason="Valid trace.",
                evidence_span_ids=["span_llm"],
            )
        ],
        diagnoses=[
            Diagnosis(
                diagnosis_id="diag_valid",
                target_type=TargetType.RUN,
                target_id="run_valid",
                failure_type="unknown",
                severity=Severity.LOW,
                summary="No issue.",
                evidence_span_ids=["span_llm"],
                suggested_fix="No action needed.",
            )
        ],
    )


def test_valid_run_passes_validation() -> None:
    validate_run(valid_run())


def test_duplicate_span_id_fails_validation() -> None:
    run = valid_run()
    duplicate = Span(
        run_id="run_valid",
        span_id="span_llm",
        name="Duplicate",
        kind=SpanKind.TOOL,
    )
    run.root_spans.append(duplicate)

    with pytest.raises(TraceValidationError, match="Duplicate span_id"):
        validate_run(run)


def test_missing_parent_fails_validation() -> None:
    run = valid_run()
    run.root_spans.append(
        Span(
            run_id="run_valid",
            span_id="span_orphan",
            parent_span_id="span_missing",
            name="Orphan",
            kind=SpanKind.TOOL,
        )
    )

    with pytest.raises(TraceValidationError, match="parent_span_id"):
        validate_run(run)


def test_child_parent_mismatch_fails_validation() -> None:
    run = valid_run()
    run.root_spans[0].children[0].parent_span_id = "span_wrong"

    with pytest.raises(TraceValidationError, match="parent mismatch"):
        validate_run(run)


def test_evaluation_evidence_must_exist() -> None:
    run = valid_run()
    run.evaluations[0].evidence_span_ids = ["span_missing"]

    with pytest.raises(TraceValidationError, match="evidence span"):
        validate_run(run)


def test_diagnosis_target_must_exist() -> None:
    run = valid_run()
    run.diagnoses[0].target_id = "span_missing"
    run.diagnoses[0].target_type = TargetType.SPAN

    with pytest.raises(TraceValidationError, match="target_id"):
        validate_run(run)
```

- [ ] **Step 2: Run validator tests to verify they fail**

Run:

```bash
pytest tests/tracing/test_validator.py -v
```

Expected: FAIL because `validator.py` does not exist.

- [ ] **Step 3: Implement validator**

Create `src/lumiagent/tracing/validator.py`:

```python
"""Structural validation for Agent traces."""
from __future__ import annotations

from .enums import TargetType
from .models import AgentRun, Span


class TraceValidationError(ValueError):
    pass


def _flatten_spans(spans: list[Span]) -> list[Span]:
    flattened: list[Span] = []
    for span in spans:
        flattened.append(span)
        flattened.extend(_flatten_spans(span.children))
    return flattened


def _validate_child_parent_links(span: Span) -> None:
    for child in span.children:
        if child.parent_span_id != span.span_id:
            raise TraceValidationError(
                f"Span {child.span_id} parent mismatch: expected {span.span_id}, got {child.parent_span_id}"
            )
        _validate_child_parent_links(child)


def _validate_target(target_type: TargetType, target_id: str, run: AgentRun, span_ids: set[str]) -> None:
    if target_type is TargetType.RUN:
        if target_id != run.run_id:
            raise TraceValidationError(f"target_id {target_id} does not match run_id {run.run_id}")
        return
    if target_id not in span_ids:
        raise TraceValidationError(f"target_id {target_id} does not reference an existing span")


def _validate_evidence(evidence_span_ids: list[str], span_ids: set[str]) -> None:
    for span_id in evidence_span_ids:
        if span_id not in span_ids:
            raise TraceValidationError(f"evidence span {span_id} does not exist")


def validate_run(run: AgentRun) -> None:
    spans = _flatten_spans(run.root_spans)
    span_ids: set[str] = set()

    for root in run.root_spans:
        if root.parent_span_id is not None:
            raise TraceValidationError(f"Root span {root.span_id} must not have parent_span_id")

    for span in spans:
        if span.run_id != run.run_id:
            raise TraceValidationError(f"Span {span.span_id} run_id does not match AgentRun {run.run_id}")
        if span.span_id in span_ids:
            raise TraceValidationError(f"Duplicate span_id {span.span_id}")
        span_ids.add(span.span_id)

    for span in spans:
        if span.parent_span_id is not None and span.parent_span_id not in span_ids:
            raise TraceValidationError(f"Span {span.span_id} parent_span_id {span.parent_span_id} does not exist")

    for root in run.root_spans:
        _validate_child_parent_links(root)

    for evaluation in run.evaluations:
        _validate_target(evaluation.target_type, evaluation.target_id, run, span_ids)
        _validate_evidence(evaluation.evidence_span_ids, span_ids)

    for diagnosis in run.diagnoses:
        _validate_target(diagnosis.target_type, diagnosis.target_id, run, span_ids)
        _validate_evidence(diagnosis.evidence_span_ids, span_ids)
```

- [ ] **Step 4: Export validator API**

Modify `src/lumiagent/tracing/__init__.py` to include:

```python
from lumiagent.tracing.validator import TraceValidationError, validate_run
```

Update `__all__` with:

```python
"TraceValidationError",
"validate_run",
```

- [ ] **Step 5: Run validator tests**

Run:

```bash
pytest tests/tracing/test_validator.py -v
```

Expected: PASS.

- [ ] **Step 6: Run tracing tests so far**

Run:

```bash
pytest tests/tracing/test_models.py tests/tracing/test_serializer.py tests/tracing/test_validator.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/lumiagent/tracing/__init__.py src/lumiagent/tracing/validator.py tests/tracing/test_validator.py
git commit -m "Add trace structure validation"
```

---

### Task 4: Add TraceBuilder convenience API

**Files:**
- Create: `src/lumiagent/tracing/builder.py`
- Modify: `src/lumiagent/tracing/__init__.py`
- Test: `tests/tracing/test_builder.py`

- [ ] **Step 1: Write failing builder tests**

Create `tests/tracing/test_builder.py`:

```python
from lumiagent.tracing import ArtifactKind, EventLevel, RunStatus, SpanKind, SpanStatus, TargetType
from lumiagent.tracing.builder import TraceBuilder
from lumiagent.tracing.validator import validate_run


def test_builder_creates_nested_trace() -> None:
    builder = TraceBuilder(run_id="run_builder", name="builder demo", input={"task": "demo"})
    agent_id = builder.start_span("Agent", kind=SpanKind.AGENT)
    llm_id = builder.start_span("LLM", kind=SpanKind.LLM, parent_span_id=agent_id, input={"prompt": "Hi"})
    builder.add_artifact(llm_id, name="prompt", kind=ArtifactKind.PROMPT, content="Hi")
    builder.add_event(llm_id, name="token_budget_warning", level=EventLevel.WARNING, message="Budget is high.")
    builder.end_span(llm_id, status=SpanStatus.SUCCESS, output={"text": "Hello"})
    builder.end_span(agent_id, status=SpanStatus.SUCCESS)
    builder.add_evaluation(
        target_type=TargetType.RUN,
        target_id="run_builder",
        name="quality",
        score=0.9,
        reason="Good trace.",
        evidence_span_ids=[llm_id],
    )
    builder.add_diagnosis(
        target_type=TargetType.RUN,
        target_id="run_builder",
        failure_type="unknown",
        summary="No issue.",
        evidence_span_ids=[llm_id],
        suggested_fix="No action needed.",
    )
    run = builder.build(status=RunStatus.SUCCESS, output={"answer": "done"})

    validate_run(run)
    assert run.status is RunStatus.SUCCESS
    assert run.root_spans[0].children[0].artifacts[0].kind is ArtifactKind.PROMPT
    assert run.evaluations[0].score == 0.9


def test_builder_rejects_unknown_parent_span() -> None:
    builder = TraceBuilder(run_id="run_builder", name="builder demo")

    try:
        builder.start_span("Bad child", kind=SpanKind.TOOL, parent_span_id="span_missing")
    except ValueError as exc:
        assert "parent_span_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run builder tests to verify they fail**

Run:

```bash
pytest tests/tracing/test_builder.py -v
```

Expected: FAIL because `builder.py` does not exist.

- [ ] **Step 3: Implement TraceBuilder**

Create `src/lumiagent/tracing/builder.py`:

```python
"""Convenience builder for Agent traces."""
from __future__ import annotations

from typing import Any, Optional

from .enums import ArtifactKind, EventLevel, RunStatus, Severity, SpanKind, SpanStatus, TargetType
from .models import AgentRun, Artifact, Diagnosis, Event, Evaluation, Span, TraceValue, utc_now
from .validator import validate_run


class TraceBuilder:
    def __init__(self, *, run_id: Optional[str] = None, name: str, input: TraceValue = None) -> None:
        self.run = AgentRun(run_id=run_id or AgentRun(name=name).run_id, name=name, status=RunStatus.RUNNING, input=input)
        self._spans: dict[str, Span] = {}

    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.CUSTOM,
        parent_span_id: Optional[str] = None,
        input: TraceValue = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        if parent_span_id is not None and parent_span_id not in self._spans:
            raise ValueError(f"parent_span_id {parent_span_id} does not exist")

        span = Span(
            run_id=self.run.run_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            status=SpanStatus.RUNNING,
            input=input,
            metadata=metadata or {},
        )
        self._spans[span.span_id] = span

        if parent_span_id is None:
            self.run.root_spans.append(span)
        else:
            self._spans[parent_span_id].children.append(span)

        return span.span_id

    def end_span(
        self,
        span_id: str,
        *,
        status: SpanStatus = SpanStatus.SUCCESS,
        output: TraceValue = None,
    ) -> None:
        span = self._get_span(span_id)
        span.status = status
        span.output = output
        span.ended_at = utc_now()

    def add_event(
        self,
        span_id: str,
        *,
        name: str,
        level: EventLevel = EventLevel.INFO,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        span = self._get_span(span_id)
        event = Event(name=name, level=level, message=message, metadata=metadata or {})
        span.events.append(event)
        return event.event_id

    def add_artifact(
        self,
        span_id: str,
        *,
        name: str,
        kind: ArtifactKind = ArtifactKind.CUSTOM,
        content: TraceValue = None,
        uri: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        span = self._get_span(span_id)
        artifact = Artifact(name=name, kind=kind, content=content, uri=uri, metadata=metadata or {})
        span.artifacts.append(artifact)
        return artifact.artifact_id

    def add_evaluation(
        self,
        *,
        target_type: TargetType,
        target_id: str,
        name: str,
        score: Optional[float] = None,
        label: Optional[str] = None,
        reason: str = "",
        evidence_span_ids: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        evaluation = Evaluation(
            target_type=target_type,
            target_id=target_id,
            name=name,
            score=score,
            label=label,
            reason=reason,
            evidence_span_ids=evidence_span_ids or [],
            metadata=metadata or {},
        )
        self.run.evaluations.append(evaluation)
        return evaluation.evaluation_id

    def add_diagnosis(
        self,
        *,
        target_type: TargetType,
        target_id: str,
        failure_type: str,
        summary: str,
        evidence_span_ids: Optional[list[str]] = None,
        suggested_fix: str,
        severity: Severity = Severity.MEDIUM,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        diagnosis = Diagnosis(
            target_type=target_type,
            target_id=target_id,
            failure_type=failure_type,
            severity=severity,
            summary=summary,
            evidence_span_ids=evidence_span_ids or [],
            suggested_fix=suggested_fix,
            metadata=metadata or {},
        )
        self.run.diagnoses.append(diagnosis)
        return diagnosis.diagnosis_id

    def build(self, *, status: RunStatus = RunStatus.SUCCESS, output: TraceValue = None) -> AgentRun:
        self.run.status = status
        self.run.output = output
        self.run.ended_at = utc_now()
        validate_run(self.run)
        return self.run

    def _get_span(self, span_id: str) -> Span:
        if span_id not in self._spans:
            raise ValueError(f"span_id {span_id} does not exist")
        return self._spans[span_id]
```

- [ ] **Step 4: Fix TraceBuilder run_id construction if tests expose duplicate temporary run issue**

If mypy or tests flag the temporary `AgentRun(name=name).run_id` pattern, replace the first line in `__init__` with this safer local import:

```python
from .models import new_id

self.run = AgentRun(run_id=run_id or new_id("run"), name=name, status=RunStatus.RUNNING, input=input)
```

Expected: no behavior change, simpler ID generation.

- [ ] **Step 5: Export builder**

Modify `src/lumiagent/tracing/__init__.py`:

```python
from lumiagent.tracing.builder import TraceBuilder
```

Update `__all__` with:

```python
"TraceBuilder",
```

- [ ] **Step 6: Run builder tests**

Run:

```bash
pytest tests/tracing/test_builder.py -v
```

Expected: PASS.

- [ ] **Step 7: Run all tracing tests**

Run:

```bash
pytest tests/tracing -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/lumiagent/tracing/__init__.py src/lumiagent/tracing/builder.py tests/tracing/test_builder.py
git commit -m "Add trace builder API"
```

---

### Task 5: Add fixture traces and fixture validation tests

**Files:**
- Create: `tests/tracing/fixtures/generic_agent_run.json`
- Create: `tests/tracing/fixtures/coding_agent_trace_sample.json`
- Modify: `tests/tracing/test_serializer.py`
- Test: `tests/tracing/test_serializer.py`

- [ ] **Step 1: Add fixture validation tests**

Append to `tests/tracing/test_serializer.py`:

```python
from pathlib import Path

from lumiagent.tracing.validator import validate_run


FIXTURES = Path(__file__).parent / "fixtures"


def test_generic_agent_run_fixture_validates() -> None:
    run = from_json((FIXTURES / "generic_agent_run.json").read_text(encoding="utf-8"))
    validate_run(run)
    assert run.root_spans[0].children[0].kind is SpanKind.RAG


def test_coding_agent_trace_sample_fixture_validates() -> None:
    run = from_json((FIXTURES / "coding_agent_trace_sample.json").read_text(encoding="utf-8"))
    validate_run(run)
    operations = [child.metadata.get("operation") for child in run.root_spans[0].children]
    assert operations == ["file_search", "file_read", "code_edit", "shell_command", "test_run"]
```

- [ ] **Step 2: Run fixture tests to verify they fail**

Run:

```bash
pytest tests/tracing/test_serializer.py::test_generic_agent_run_fixture_validates tests/tracing/test_serializer.py::test_coding_agent_trace_sample_fixture_validates -v
```

Expected: FAIL because fixture files do not exist.

- [ ] **Step 3: Create generic fixture**

Create `tests/tracing/fixtures/generic_agent_run.json`:

```json
{
  "run_id": "run_generic_fixture",
  "name": "Generic Agent Run",
  "status": "success",
  "started_at": "2026-05-24T12:00:00Z",
  "ended_at": "2026-05-24T12:00:06Z",
  "input": {"question": "How does provider fallback work?"},
  "output": {"answer": "The router switches to a fallback provider and records the failure."},
  "metadata": {"scenario": "generic_agent"},
  "root_spans": [
    {
      "span_id": "span_generic_agent",
      "run_id": "run_generic_fixture",
      "parent_span_id": null,
      "name": "Agent workflow",
      "kind": "agent",
      "status": "success",
      "started_at": "2026-05-24T12:00:00Z",
      "ended_at": "2026-05-24T12:00:06Z",
      "input": null,
      "output": null,
      "metadata": {},
      "events": [],
      "artifacts": [],
      "children": [
        {
          "span_id": "span_generic_rag",
          "run_id": "run_generic_fixture",
          "parent_span_id": "span_generic_agent",
          "name": "Retrieve docs",
          "kind": "rag",
          "status": "success",
          "started_at": "2026-05-24T12:00:01Z",
          "ended_at": "2026-05-24T12:00:02Z",
          "input": {"query": "provider fallback"},
          "output": {"top_k": 2},
          "metadata": {},
          "events": [],
          "artifacts": [
            {
              "artifact_id": "artifact_retrieved_chunks",
              "name": "retrieved chunks",
              "kind": "retrieved_chunks",
              "uri": null,
              "content": [{"chunk_id": "doc_1", "score": 0.92, "text": "Fallback providers are tried after primary failure."}],
              "metadata": {}
            }
          ],
          "children": []
        },
        {
          "span_id": "span_generic_llm",
          "run_id": "run_generic_fixture",
          "parent_span_id": "span_generic_agent",
          "name": "Generate answer",
          "kind": "llm",
          "status": "success",
          "started_at": "2026-05-24T12:00:02Z",
          "ended_at": "2026-05-24T12:00:04Z",
          "input": {"model": "demo-model"},
          "output": {"text": "Fallback is recorded in trace metadata."},
          "metadata": {"token_usage": {"prompt": 120, "completion": 30}},
          "events": [],
          "artifacts": [
            {"artifact_id": "artifact_prompt", "name": "prompt", "kind": "prompt", "uri": null, "content": "Explain provider fallback.", "metadata": {}},
            {"artifact_id": "artifact_completion", "name": "completion", "kind": "completion", "uri": null, "content": "Fallback is recorded in trace metadata.", "metadata": {}}
          ],
          "children": []
        },
        {
          "span_id": "span_generic_tool",
          "run_id": "run_generic_fixture",
          "parent_span_id": "span_generic_agent",
          "name": "Inspect router config",
          "kind": "tool",
          "status": "success",
          "started_at": "2026-05-24T12:00:04Z",
          "ended_at": "2026-05-24T12:00:05Z",
          "input": {"tool": "read_config"},
          "output": {"fallback": "enabled"},
          "metadata": {},
          "events": [],
          "artifacts": [{"artifact_id": "artifact_tool_result", "name": "tool result", "kind": "tool_result", "uri": null, "content": {"fallback": "enabled"}, "metadata": {}}],
          "children": []
        },
        {
          "span_id": "span_generic_evaluator",
          "run_id": "run_generic_fixture",
          "parent_span_id": "span_generic_agent",
          "name": "Evaluate answer",
          "kind": "evaluator",
          "status": "success",
          "started_at": "2026-05-24T12:00:05Z",
          "ended_at": "2026-05-24T12:00:06Z",
          "input": {"metric": "groundedness"},
          "output": {"score": 0.9},
          "metadata": {},
          "events": [],
          "artifacts": [],
          "children": []
        }
      ]
    }
  ],
  "evaluations": [
    {"evaluation_id": "eval_generic_quality", "target_type": "run", "target_id": "run_generic_fixture", "name": "answer_quality", "score": 0.9, "label": "pass", "reason": "The answer uses retrieved context.", "evidence_span_ids": ["span_generic_rag", "span_generic_llm"], "metadata": {}}
  ],
  "diagnoses": [
    {"diagnosis_id": "diag_generic", "target_type": "run", "target_id": "run_generic_fixture", "failure_type": "unknown", "severity": "low", "summary": "No blocking issue found.", "evidence_span_ids": ["span_generic_evaluator"], "suggested_fix": "No action needed.", "metadata": {}}
  ]
}
```

- [ ] **Step 4: Create coding-agent fixture**

Create `tests/tracing/fixtures/coding_agent_trace_sample.json`:

```json
{
  "run_id": "run_coding_fixture",
  "name": "Coding Agent Trace Sample",
  "status": "success",
  "started_at": "2026-05-24T13:00:00Z",
  "ended_at": "2026-05-24T13:00:10Z",
  "input": {"task": "Fix the login button label."},
  "output": {"summary": "Updated label and ran tests."},
  "metadata": {"scenario": "coding_agent"},
  "root_spans": [
    {
      "span_id": "span_coding_agent",
      "run_id": "run_coding_fixture",
      "parent_span_id": null,
      "name": "Coding workflow",
      "kind": "agent",
      "status": "success",
      "started_at": "2026-05-24T13:00:00Z",
      "ended_at": "2026-05-24T13:00:10Z",
      "input": null,
      "output": null,
      "metadata": {},
      "events": [],
      "artifacts": [],
      "children": [
        {"span_id": "span_file_search", "run_id": "run_coding_fixture", "parent_span_id": "span_coding_agent", "name": "Search files", "kind": "tool", "status": "success", "started_at": "2026-05-24T13:00:01Z", "ended_at": "2026-05-24T13:00:02Z", "input": {"pattern": "login"}, "output": {"files": ["src/auth/LoginButton.tsx"]}, "metadata": {"operation": "file_search"}, "events": [], "artifacts": [], "children": []},
        {"span_id": "span_file_read", "run_id": "run_coding_fixture", "parent_span_id": "span_coding_agent", "name": "Read file", "kind": "tool", "status": "success", "started_at": "2026-05-24T13:00:02Z", "ended_at": "2026-05-24T13:00:03Z", "input": {"path": "src/auth/LoginButton.tsx"}, "output": {"lines": 80}, "metadata": {"operation": "file_read"}, "events": [], "artifacts": [], "children": []},
        {"span_id": "span_code_edit", "run_id": "run_coding_fixture", "parent_span_id": "span_coding_agent", "name": "Edit code", "kind": "tool", "status": "success", "started_at": "2026-05-24T13:00:03Z", "ended_at": "2026-05-24T13:00:05Z", "input": {"path": "src/auth/LoginButton.tsx"}, "output": {"changed_lines": 1}, "metadata": {"operation": "code_edit"}, "events": [], "artifacts": [{"artifact_id": "artifact_code_diff", "name": "code diff", "kind": "code_diff", "uri": null, "content": "- Sign in\n+ Log in", "metadata": {}}], "children": []},
        {"span_id": "span_shell_command", "run_id": "run_coding_fixture", "parent_span_id": "span_coding_agent", "name": "Run typecheck", "kind": "tool", "status": "success", "started_at": "2026-05-24T13:00:05Z", "ended_at": "2026-05-24T13:00:08Z", "input": {"command": "npm run typecheck"}, "output": {"exit_code": 0}, "metadata": {"operation": "shell_command"}, "events": [], "artifacts": [], "children": []},
        {"span_id": "span_test_run", "run_id": "run_coding_fixture", "parent_span_id": "span_coding_agent", "name": "Run tests", "kind": "tool", "status": "success", "started_at": "2026-05-24T13:00:08Z", "ended_at": "2026-05-24T13:00:10Z", "input": {"command": "npm test"}, "output": {"exit_code": 0}, "metadata": {"operation": "test_run"}, "events": [], "artifacts": [{"artifact_id": "artifact_test_output", "name": "test output", "kind": "test_output", "uri": null, "content": "3 passed", "metadata": {}}], "children": []}
      ]
    }
  ],
  "evaluations": [
    {"evaluation_id": "eval_verification", "target_type": "run", "target_id": "run_coding_fixture", "name": "verification_sufficiency", "score": 1.0, "label": "pass", "reason": "The agent ran typecheck and tests after editing code.", "evidence_span_ids": ["span_shell_command", "span_test_run"], "metadata": {}}
  ],
  "diagnoses": [
    {"diagnosis_id": "diag_coding", "target_type": "run", "target_id": "run_coding_fixture", "failure_type": "unknown", "severity": "low", "summary": "The workflow includes context gathering, editing, and verification.", "evidence_span_ids": ["span_file_read", "span_code_edit", "span_test_run"], "suggested_fix": "No action needed.", "metadata": {}}
  ]
}
```

- [ ] **Step 5: Run fixture tests**

Run:

```bash
pytest tests/tracing/test_serializer.py -v
```

Expected: PASS.

- [ ] **Step 6: Run all tracing tests**

Run:

```bash
pytest tests/tracing -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/tracing/test_serializer.py tests/tracing/fixtures/generic_agent_run.json tests/tracing/fixtures/coding_agent_trace_sample.json
git commit -m "Add trace fixture samples"
```

---

### Task 6: Run full validation suite and update public exports

**Files:**
- Modify: `src/lumiagent/__init__.py` if needed for top-level version-safe exports
- Modify: `README.md` only if a tiny Trace Core note is desired; skip if it would distract from current README overhaul
- Test: full project checks

- [ ] **Step 1: Inspect current package init**

Run:

```bash
python - <<'PY'
from pathlib import Path
print(Path('src/lumiagent/__init__.py').read_text())
PY
```

Expected: see current package exports. If it only contains version metadata, do not add large top-level exports.

- [ ] **Step 2: Verify tracing package imports**

Run:

```bash
python - <<'PY'
from lumiagent.tracing import AgentRun, Span, SpanKind, TraceBuilder, validate_run
print(AgentRun.__name__, Span.__name__, SpanKind.AGENT.value, TraceBuilder.__name__, validate_run.__name__)
PY
```

Expected output contains:

```text
AgentRun Span agent TraceBuilder validate_run
```

- [ ] **Step 3: Run all tracing tests**

Run:

```bash
pytest tests/tracing -v
```

Expected: PASS.

- [ ] **Step 4: Run all tests**

Run:

```bash
pytest -v
```

Expected: PASS. If only `tests/tracing` exists, this should run the tracing suite.

- [ ] **Step 5: Run lint if available**

Run:

```bash
ruff check src/lumiagent/tracing tests/tracing
```

Expected: PASS.

- [ ] **Step 6: Run type checking if dependencies are available**

Run:

```bash
mypy src/lumiagent/tracing
```

Expected: PASS. If mypy fails because project-wide config includes unrelated existing issues, capture the failure and do not broaden scope unless the failure is inside `src/lumiagent/tracing`.

- [ ] **Step 7: Final git status check**

Run:

```bash
git status --short
```

Expected: clean working tree after prior commits, or only intentionally uncommitted documentation if you chose to update README.

- [ ] **Step 8: Commit final export/docs adjustments if any**

If files changed in this task:

```bash
git add src/lumiagent/__init__.py README.md
git commit -m "Expose trace core package"
```

If no files changed, skip the commit.

---

## Self-Review

Spec coverage:

- AgentRun, Span, Event, Artifact, Evaluation, Diagnosis models: Task 1.
- JSON serialization and deserialization: Task 2.
- Trace structural validation: Task 3.
- Builder API: Task 4.
- Generic and Coding Agent sample traces: Task 5.
- Test and architecture verification: Task 6.

Placeholder scan:

- No TBD/TODO placeholders remain.
- Each implementation step includes concrete code or exact commands.

Type consistency:

- `AgentRun`, `Span`, `Event`, `Artifact`, `Evaluation`, `Diagnosis` are consistently exported from `lumiagent.tracing`.
- Enum names are consistently `RunStatus`, `SpanStatus`, `SpanKind`, `EventLevel`, `ArtifactKind`, `TargetType`, `Severity`.
- Serializer helpers are consistently `to_dict`, `to_json`, `from_dict`, `from_json`.
- Validator entrypoint is consistently `validate_run`.
- Builder class is consistently `TraceBuilder`.
