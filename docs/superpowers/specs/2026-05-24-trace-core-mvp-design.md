# LumiAgent Trace Core MVP Requirements Specification

## 1. Version Goal

The first version establishes LumiAgent's minimum core capability:

```text
Agent Trace / Eval Core
```

The goal is to give LumiAgent a stable data foundation that can represent one Agent execution flow with a unified model.

This version does not integrate real Coding Agents, Claude Code, MCP Servers, LangChain, LangGraph, or frontend UI. It focuses only on:

```text
Agent Run modeling
Span Tree modeling
Event / Artifact modeling
Evaluation / Diagnosis modeling
JSON serialization and deserialization
Trace structural validation
Example traces
Unit tests
```

The success criterion is:

```text
LumiAgent can represent one Agent Run with a stable, extensible, and verifiable data model.
```

## 2. Design Principles

### 2.1 Trace is a first-class product concept

LumiAgent should first be able to record, represent, evaluate, and diagnose Agent execution. The first version is data-model centric, not runtime-, provider-, executor-, or UI-centric.

### 2.2 Core and Adapter separation

The first version only implements the general Core, not concrete adapters.

```text
Core:
General representation for LLM / Tool / RAG / Memory / Evaluator / Error spans

Adapters:
Claude Code / MCP / LangChain / LangGraph / CLI Agent integrations
```

Coding Agent and MCP scenarios may appear only in sample traces.

### 2.3 Extensibility first

The Span model must support future extensions:

```text
Coding Agent Trace
MCP Tool Chain
Trace Replay UI
Evaluation Engine
Diagnosis Engine
Experiment Compare
```

The first version must not prematurely implement these complete capabilities.

### 2.4 Verifiability first

Every first-version capability must be testable:

```text
model creation
span nesting
JSON serialization
JSON deserialization
trace validation
invalid trace detection
evaluation / diagnosis evidence validation
```

## 3. Scope

### 3.1 AgentRun

Represents one complete Agent execution.

Fields:

```text
run_id: string
name: string
status: RunStatus
started_at: datetime
ended_at: datetime | null
input: dict | list | string | null
output: dict | list | string | null
metadata: dict
root_spans: list[Span]
evaluations: list[Evaluation]
diagnoses: list[Diagnosis]
```

RunStatus:

```text
pending
running
success
error
cancelled
```

Requirements:

- `run_id` must be unique.
- Spans in `root_spans` must not have a parent.
- `ended_at = null` means the run has not ended.
- If `ended_at` exists, `started_at <= ended_at` must hold.

### 3.2 Span

Represents one execution step. Span is the core object of LumiAgent Trace Core.

Fields:

```text
span_id: string
run_id: string
parent_span_id: string | null
name: string
kind: SpanKind
status: SpanStatus
started_at: datetime
ended_at: datetime | null
input: dict | list | string | null
output: dict | list | string | null
metadata: dict
events: list[Event]
artifacts: list[Artifact]
children: list[Span]
```

SpanKind:

```text
agent
llm
tool
rag
memory
evaluator
fallback
error
custom
```

SpanStatus:

```text
pending
running
success
error
skipped
cancelled
```

Requirements:

- `span_id` must be unique within the same run.
- `parent_span_id = null` means root span.
- If `parent_span_id` is not null, it must point to an existing span in the same run.
- A child span's `parent_span_id` must equal its parent span's `span_id`.
- If `ended_at` exists, `started_at <= ended_at` must hold.
- `kind` and `status` must be valid enum values.

### 3.3 Event

Represents a lightweight event inside a span.

Fields:

```text
event_id: string
name: string
timestamp: datetime
level: EventLevel
message: string
metadata: dict
```

EventLevel:

```text
debug
info
warning
error
```

Examples:

```text
tool_argument_validated
fallback_triggered
retry_started
token_budget_warning
command_failed
```

### 3.4 Artifact

Represents a large object produced or referenced by a span.

Fields:

```text
artifact_id: string
name: string
kind: ArtifactKind
uri: string | null
content: dict | list | string | null
metadata: dict
```

ArtifactKind:

```text
prompt
completion
retrieved_chunks
tool_result
code_diff
test_output
log
custom
```

Requirements:

- At least one of `content` or `uri` should exist.
- Inline `content` is allowed in the first version.
- `uri` is reserved for future external object storage, filesystem, or database references.

### 3.5 Evaluation

Represents an evaluation result for a run or span.

Fields:

```text
evaluation_id: string
target_type: TargetType
target_id: string
name: string
score: float | null
label: string | null
reason: string
evidence_span_ids: list[string]
metadata: dict
```

TargetType:

```text
run
span
```

Requirements:

- `target_id` must point to an existing run or span.
- If `score` exists, it must be between `0.0` and `1.0`.
- `label` may be used for values such as `pass`, `fail`, or `warning`.
- All `evidence_span_ids` must point to existing spans.
- Evaluation should be traceable to evidence spans unless it is a global run-level evaluation and `reason` explains the scope.

### 3.6 Diagnosis

Represents failure attribution or optimization suggestions.

Fields:

```text
diagnosis_id: string
target_type: TargetType
target_id: string
failure_type: string
severity: Severity
summary: string
evidence_span_ids: list[string]
suggested_fix: string
metadata: dict
```

Severity:

```text
low
medium
high
critical
```

Suggested first-version failure types:

```text
context_gap
tool_misuse
argument_error
result_misinterpretation
insufficient_verification
failure_recovery_gap
risk_control_issue
unknown
```

Requirements:

- `target_id` must point to an existing run or span.
- All `evidence_span_ids` must point to existing spans.
- `summary` must explain the issue.
- `suggested_fix` must provide an actionable recommendation.

## 4. JSON Serialization and Deserialization

The first version must support:

```text
AgentRun -> JSON
JSON -> AgentRun
```

Requirements:

- Use stable field names.
- Datetimes use ISO 8601.
- Enums serialize as strings.
- `None` / `null` represents missing optional fields.
- Deserialized models must be semantically equivalent to the original models.
- Output JSON should serve as the shared format for future UI, fixtures, CLI, and APIs.

## 5. Trace Validation Rules

### 5.1 Run validation

```text
run_id is not empty
name is not empty
status is valid
started_at is valid
started_at <= ended_at if ended_at exists
```

### 5.2 Span validation

```text
span_id is not empty
span_id is unique within the run
run_id matches the owning AgentRun
kind is valid
status is valid
parent_span_id exists or is null
children parent_span_id matches parent span
started_at <= ended_at if ended_at exists
```

### 5.3 Event validation

```text
event_id is not empty
name is not empty
timestamp is valid
level is valid
```

### 5.4 Artifact validation

```text
artifact_id is not empty
name is not empty
kind is valid
content or uri exists
```

### 5.5 Evaluation validation

```text
evaluation_id is not empty
target_type is valid
target_id exists
score is null or between 0.0 and 1.0
all evidence_span_ids exist
```

### 5.6 Diagnosis validation

```text
diagnosis_id is not empty
target_type is valid
target_id exists
severity is valid
summary is not empty
suggested_fix is not empty
all evidence_span_ids exist
```

## 6. Example Traces

The first version must include at least two fixture examples.

### 6.1 `generic_agent_run.json`

Purpose: prove that a general Agent execution can be represented.

Suggested structure:

```text
Agent Run
└── agent span
    ├── rag span
    ├── llm span
    ├── tool span
    └── evaluator span
```

Includes:

```text
RAG retrieval artifact
LLM prompt artifact
LLM completion artifact
Tool result artifact
Evaluation
Diagnosis
```

### 6.2 `coding_agent_trace_sample.json`

Purpose: prove that the general model can represent a Coding Agent workflow.

Important: this version does not implement a real Coding Agent Adapter. This is fixture-only.

Suggested structure:

```text
Coding Agent Run
└── agent span
    ├── file_search span
    ├── file_read span
    ├── code_edit span
    ├── shell_command span
    ├── test_run span
    └── diagnosis span / run-level diagnosis
```

Coding-Agent-specific information should be represented as:

```text
kind = tool or custom
metadata.operation = file_search / code_edit / test_run
```

This avoids adding too many specialized SpanKind values in the first version.

## 7. Proposed Code Structure

Add a standalone tracing module:

```text
src/lumiagent/tracing/
├── __init__.py
├── enums.py
├── models.py
├── serializer.py
├── validator.py
└── builder.py
```

### 7.1 `enums.py`

Defines:

```text
RunStatus
SpanStatus
SpanKind
EventLevel
ArtifactKind
TargetType
Severity
```

### 7.2 `models.py`

Defines:

```text
AgentRun
Span
Event
Artifact
Evaluation
Diagnosis
```

### 7.3 `serializer.py`

Responsible for:

```text
to_json
from_json
to_dict
from_dict
```

### 7.4 `validator.py`

Responsible for:

```text
validate_run
validate_span_tree
validate_evidence_refs
validate_time_ranges
```

### 7.5 `builder.py`

Provides convenient construction API:

```text
TraceBuilder
start_run
start_span
end_span
add_event
add_artifact
add_evaluation
add_diagnosis
build
```

The first-version builder can stay simple and should not implement async context managers.

## 8. Testing Requirements

Add:

```text
tests/tracing/
├── test_models.py
├── test_serializer.py
├── test_validator.py
├── test_builder.py
└── fixtures/
    ├── generic_agent_run.json
    └── coding_agent_trace_sample.json
```

Required test scenarios:

```text
create AgentRun
create nested Span
add Event
add Artifact
add Evaluation
add Diagnosis
JSON round-trip
invalid parent_span_id
duplicate span_id
invalid evidence_span_ids
invalid score
artifact with both content and uri empty
started_at > ended_at
```

Test constraints:

```text
no real LLM API
no MCP Server
no database
no Web service
```

## 9. Architecture Boundaries

The first-version tracing module must not depend on:

```text
lumiagent.llm
lumiagent.tools
lumiagent.rag
lumiagent.platform
FastAPI
ChromaDB
MCP SDK
```

Allowed dependencies:

```text
standard library
pydantic
typing
datetime
uuid
```

This keeps Trace Core stable, lightweight, and reusable.

## 10. Acceptance Criteria

### 10.1 Functional acceptance

```text
1. Can create AgentRun
2. Can add nested Span
3. Can add Event and Artifact
4. Can add Evaluation and Diagnosis
5. Can export JSON
6. Can load from JSON
7. Can validate legal traces
8. Can reject illegal traces
```

### 10.2 Example acceptance

```text
1. generic_agent_run.json passes validator
2. coding_agent_trace_sample.json passes validator
3. coding_agent_trace_sample.json can represent a basic Coding Agent workflow
```

### 10.3 Test acceptance

```text
pytest tests/tracing passes
```

The test suite must cover at least:

```text
model creation
Span nesting
serialization / deserialization
validator success path
validator failure paths
builder basic path
```

### 10.4 Architecture acceptance

```text
1. tracing module remains independent
2. no external Agent framework is introduced
3. no real LLM / MCP / RAG dependency is introduced
4. Coding Agent and MCP appear only as sample trace / metadata in this version
```

## 11. Next Phases

After this version is complete, proceed in order:

```text
Phase 2: MCP Tool Chain Model
Phase 3: Coding Agent Trace Model
Phase 4: Evaluation / Diagnosis Engine
Phase 5: Replay / Visualization Data Model
```

Do not implement these full capabilities in the first version.

## 12. Conclusion

The first-version requirement is:

```text
Build Trace Core before integrating Agents.
```

Without a stable Trace Core, MCP integration, Coding Agent trace capture, Evaluation, and Replay UI would become one-off logic. Trace Core MVP is the foundation for all future LumiAgent capabilities.
