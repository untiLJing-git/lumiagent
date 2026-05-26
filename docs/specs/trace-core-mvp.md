# Trace Core MVP Specification

## 1. Purpose

Phase 1 establishes the LumiAgent Trace Core MVP. Its purpose is to create a stable, framework-agnostic data foundation for representing one Agent execution as a structured Span Tree.

This phase is data-model centric. It does not integrate real Coding Agents, MCP Servers, Claude Code, LangChain, LangGraph, or UI components.

## 2. Product Value

LumiAgent treats traces as first-class product data. The Trace Core gives later phases a shared representation for recording, replaying, evaluating, and diagnosing Agent runs.

The core answers foundational questions:

- What happened during one Agent run?
- Which execution steps were nested under which parent step?
- What events and artifacts were produced by each step?
- Which spans support an evaluation or diagnosis?
- Can the trace be serialized, loaded, and validated consistently?

Without this core, Coding Agent Trace, MCP Tool Chain evidence, replay views, and diagnosis engines would each invent incompatible data shapes.

## 3. Scope

Phase 1 defines the generic Trace Core:

```text
AgentRun
Span
Event
Artifact
Evaluation
Diagnosis
```

It also defines:

```text
RunStatus
SpanKind
SpanStatus
EventLevel
ArtifactKind
TargetType
Severity
```

The implementation includes JSON/dict serialization, deserialization, structural validation, example fixtures, unit tests, and a convenience `TraceBuilder` API.

## 4. Non-goals

Phase 1 does not include:

- Real Coding Agent integration.
- Real MCP SDK or MCP Server integration.
- Claude Code, LangChain, or LangGraph adapters.
- Runtime trace capture hooks.
- UI, dashboard, timeline, or replay rendering.
- Automatic evaluator or diagnosis engine logic.
- Persistent storage or object storage.
- A large all-purpose Agent framework.

Coding Agent and MCP scenarios may appear only as sample trace data.

## 5. Core Models

### 5.1 AgentRun

Represents one complete Agent execution.

Required capabilities:

- Unique `run_id`.
- Human-readable `name`.
- Lifecycle status via `RunStatus`.
- `started_at` and optional `ended_at`.
- Generic `input`, `output`, and `metadata` fields.
- Root spans through `root_spans`.
- Run- or span-level `evaluations` and `diagnoses`.

### 5.2 Span

Represents one execution step. Spans form a tree through `parent_span_id` and `children`.

Required capabilities:

- Unique `span_id` within a run.
- Reference to the owning `run_id`.
- Optional parent span reference.
- Generic `kind`, `status`, timing, input, output, and metadata.
- Child spans, events, and artifacts.

`SpanKind` remains generic:

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

Adapter-specific semantics should be expressed with metadata or adapter-layer conventions, not by expanding Core for every protocol.

### 5.3 Event

Represents a lightweight timestamped event inside a span.

Required capabilities:

- Unique `event_id`.
- Event `name`.
- Timestamp.
- Level via `EventLevel`.
- Message and metadata.

### 5.4 Artifact

Represents a larger object produced or referenced by a span.

Required capabilities:

- Unique `artifact_id`.
- Artifact `name` and `kind`.
- Inline `content` or external `uri`.
- Metadata for adapter-specific meaning.

At least one of `content` or `uri` must exist.

### 5.5 Evaluation

Represents an evaluation result for a run or span.

Required capabilities:

- Target reference through `target_type` and `target_id`.
- Name, optional score, optional label, and reason.
- Evidence span references through `evidence_span_ids`.
- Metadata for evaluator-specific data.

Scores must be between `0.0` and `1.0` when present.

### 5.6 Diagnosis

Represents failure attribution or an optimization suggestion.

Required capabilities:

- Target reference through `target_type` and `target_id`.
- String `failure_type` so later phases can define adapter-specific taxonomies.
- Severity, summary, evidence span references, suggested fix, and metadata.

## 6. Serialization

The Trace Core supports:

```text
AgentRun -> dict
AgentRun -> JSON
JSON -> AgentRun
```

Requirements:

- Stable field names.
- Enums serialize as strings.
- Datetimes serialize as ISO 8601 values.
- `None` serializes as `null`.
- Deserialized traces remain semantically equivalent to the original model.

## 7. Validation

The Trace Core validates structural correctness:

- Root spans must not have `parent_span_id`.
- Span IDs must be unique within a run.
- Child span `parent_span_id` must match the parent span.
- Non-root parent references must point to an existing span in the same run.
- Span `run_id` must match the owning `AgentRun`.
- Evaluation and diagnosis targets must reference an existing run or span.
- Evidence span IDs must reference existing spans.
- Time ranges must satisfy `started_at <= ended_at` when `ended_at` exists.

## 8. Fixtures and Tests

Phase 1 includes trace fixtures for:

```text
generic_agent_run.json
coding_agent_trace_sample.json
```

Test coverage includes:

- Model creation.
- Span nesting.
- Event, artifact, evaluation, and diagnosis creation.
- Serialization to dict and JSON.
- Deserialization from dict and JSON.
- Structural validation success and failure cases.
- Convenience `TraceBuilder` behavior.

## 9. Acceptance Criteria

Phase 1 is complete when:

- A simple Agent Run can be represented as a unified Span Tree.
- The trace can be serialized into stable JSON and loaded back.
- Tests cover model creation, nesting, serialization, deserialization, validation, and builder behavior.
- Example fixtures validate as `AgentRun` objects.
- The implementation remains framework-agnostic.
- Coding Agent and MCP support remain outside Core except as sample data.

## 10. Relationship to Later Phases

Phase 1 is the foundation for all later work:

```text
Phase 2 MCP Tool Chain Model:
  uses Core spans, events, artifacts, and metadata conventions

Phase 3 Coding Agent Trace Model:
  uses Core to represent full coding workflows

Phase 4 Evaluation / Diagnosis Engine:
  uses Evaluation, Diagnosis, and evidence span references

Phase 5 Replay / Visualization Preparation:
  uses serialized AgentRun and Span Tree data
```

The Core should remain stable and generic. New protocol- or workflow-specific semantics should first be modeled as adapter conventions unless a future project specification explicitly changes the Core.
