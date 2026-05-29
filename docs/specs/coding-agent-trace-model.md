# Coding Agent Trace Model Specification

## 1. Purpose

Phase 3 establishes LumiAgent's framework-agnostic semantic Coding Agent Trace Model and validates it through Claude Code as the first real Coding Agent capture adapter.

The phase should model more than tool calls. It must express how a Coding Agent moves from user intent to task understanding, context gathering, action execution, code modification, verification, error observation, recovery, result interpretation, final response, and trace review findings.

```text
user intent
  -> task understanding
  -> context gathering
  -> action/tool evidence
  -> code modification
  -> verification
  -> error observation / recovery
  -> result interpretation
  -> final response
  -> workflow review findings
```

Phase 3 uses:

- **Hooks evidence** for stable action facts: file search, file read, edits, commands, tests, tool errors, latency, and permissions.
- **Transcript enrichment** for semantic context: user request, task understanding, plans, summaries, result interpretation, and final response.
- **TraceWriter** for incremental Coding Agent capture: hooks events -> normalized coding events -> AgentRun.
- **Workflow validator** for deterministic, high-confidence trace review findings. It does not replace Phase 4 Evaluation / Diagnosis.

One-sentence positioning:

> Phase 3 builds a Generic Semantic Coding Trace Core and uses Claude Code hooks plus minimal transcript enrichment as the first real Capture Adapter, proving that a coding workflow can be captured, normalized, converted, pre-checked, and reviewed.

## 2. Scope

### 2.1 Coding Agent Trace Conventions

Phase 3 models Coding Agent behavior by semantic action, not by individual Claude Code tool names.

Stable Phase 3 conventions:

```text
user_prompt
task_understanding
context_gathering
file_search
file_read
code_edit
shell_command
test_run
verification
git_diff
error_observed
failure_recovery
result_interpretation
permission_request
approval_decision
final_response
workflow_check
```

These conventions should be represented through span metadata, events, and artifacts. Phase 3 should avoid adding many new Core `SpanKind` values and must not add Claude Code-specific fields to Trace Core.

### 2.2 Evidence Model

Phase 3 defines two evidence categories:

- `action_evidence`: structured action evidence from hooks, such as tool name, arguments, result, exit code, error, duration, and permission state.
- `semantic_evidence`: semantic evidence from transcript enrichment, such as user prompt, assistant plan or summary, result interpretation, and final response.

A span may carry action evidence, semantic evidence, or both.

### 2.3 Claude Code Hooks Capture Adapter

Phase 3 implements the Claude Code capture path:

```text
lumiagent setup claude-code
  -> registers hooks in .claude/settings.json

Claude Code session
  -> hooks write .lumiagent/sessions/<session-id>/events.jsonl

lumiagent trace <session-id> -o trace.json
  -> converts events plus optional transcript enrichment to AgentRun
```

LumiAgent owns the intermediate `events.jsonl` format. Stability depends on documented Claude Code hooks firing, not on Claude Code internal transcript format.

### 2.4 Minimal Transcript Enrichment

Transcript enrichment is best-effort and isolated in the Claude Code adapter layer.

It should extract, when available:

- user prompt;
- assistant final response;
- assistant plan or summary;
- result interpretation.

Transcript enrichment must not block hooks-only conversion. If transcript data is missing, unsupported, or parse fails, the converter should still produce a valid hooks-only trace when hook events are valid.

### 2.5 TraceWriter for Incremental Coding Capture

Phase 3 uses `TraceWriter` as the write boundary for incremental Coding Agent capture:

```text
normalized coding events
  -> TraceWriter
  -> AgentRun
```

TraceWriter is not the universal trace construction interface for every adapter. Phase 2b MCP capture remains on the `McpTraceMapper` + `TraceBuilder` path. Phase 3 does not refactor `McpTraceMapper`.

Phase 3 TraceWriter constraints:

- provide a minimal usable implementation for the hooks converter;
- do not implement production-grade storage, concurrency, cloud/database sinks, or streaming servers;
- do not turn TraceWriter into a general observability SDK.

### 2.6 Workflow Validator as Trace Review

Phase 3 implements deterministic, structured, high-confidence workflow checks and presents them as trace review findings.

Example checks:

- `code_edit` without later `test_run` or `verification`;
- failed `test_run` without recovery;
- failed `shell_command` without recovery;
- denied permission followed by related risky action;
- final response after unresolved error.

Findings should be shown as part of trace review:

```text
lumiagent show trace.json
  -> Span Tree
  -> Semantic Summary
  -> Workflow Checks
```

Workflow checks are not Phase 4 Evaluation / Diagnosis records by default.

### 2.7 MCP Compatibility

Phase 3 does not redefine MCP taxonomy. MCP spans and artifacts from Phase 2b can be embedded or referenced where a Coding Agent uses MCP tools:

```text
mcp_tool_chain
mcp_connection
mcp_discovery
mcp_tool_selection
mcp_tool_execution
mcp_failure_evidence
```

MCP batch mapping remains separate from incremental TraceWriter usage.

### 2.8 Fixtures and Verification

Phase 3 delivers:

- stable synthetic Coding Agent trace fixtures;
- at least one sanitized and minimized real Claude Code session fixture;
- raw real capture data retained locally, not committed;
- unit, integration, and CLI verification;
- a Chinese technical report.

## 3. Non-goals

Phase 3 does not include:

- Phase 4 Evaluation / Diagnosis Engine;
- LLM-based diagnosis, final scores, or complex suggested fixes;
- full Claude Code internal transcript reconstruction;
- treating Claude Code transcript format as a stable contract;
- refactoring Phase 2b `McpTraceMapper`;
- Web UI, TUI, replay view models, or trace diff;
- generic SDK decorators;
- MCP proxy;
- realtime trace streaming server;
- database or cloud writer;
- production-grade TraceWriter concurrency or storage;
- generic LLM observability dashboard behavior.

## 4. Architecture

### 4.1 Overview

Phase 3 architecture has four layers:

```text
Capture Sources
  -> Normalization / Enrichment
  -> Trace Construction
  -> Review / Validation
```

Detailed flow:

```text
Claude Code hooks events       Optional transcript
          │                           │
          ▼                           ▼
  HookEventReader              TranscriptEnrichmentStrategy
          │                           │
          └──────────┬────────────────┘
                     ▼
          CodingEventNormalizer
                     │
                     ▼
              TraceWriter
                     │
                     ▼
                 AgentRun
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
 WorkflowValidator       CLI Viewer / show
```

Core principles:

- capture sources can later include SDK decorators, proxies, transcript importers, or other agents;
- normalization maps source-specific events into Coding Agent semantic conventions;
- trace construction targets Trace Core, not Claude Code internals;
- review and validation consume standard `AgentRun` traces and do not depend on the capture source.

### 4.2 Recommended Module Boundaries

Recommended modules:

```text
src/lumiagent/adapters/coding/
  __init__.py
  conventions.py
  events.py
  normalizer.py
  validator.py
  viewer.py

src/lumiagent/adapters/claude_code/
  __init__.py
  hooks.py
  setup.py
  events.py
  transcript.py
  converter.py
  sanitizer.py

src/lumiagent/tracing/
  writer.py
  builder_writer.py
```

`adapters/coding/` owns framework-agnostic Coding Agent semantics:

- conventions;
- normalized coding event schemas;
- tool/action classification;
- workflow validator;
- Coding Agent viewer helpers.

`adapters/claude_code/` owns Claude Code-specific capture:

- hook entrypoint and setup;
- Claude Code hook event schema;
- transcript enrichment;
- source event conversion;
- sanitization.

`tracing/builder_writer.py` provides the minimal `TraceWriter` implementation, likely wrapping the existing `TraceBuilder`.

## 5. Data Flow

### 5.1 Hooks-only Flow

```text
Claude Code session
  -> hook payloads
  -> .lumiagent/sessions/<session-id>/events.jsonl
  -> HookEventReader
  -> CodingEventNormalizer
  -> TraceWriter
  -> AgentRun
  -> trace.json
  -> WorkflowValidator
  -> lumiagent show
```

This is the stable required path and does not depend on transcript availability.

### 5.2 Hooks + Transcript Enrichment Flow

```text
Claude Code session
  -> hook payloads
  -> events.jsonl
  -> optional transcript
  -> TranscriptEnrichmentStrategy
  -> normalized action + semantic events
  -> TraceWriter
  -> AgentRun with action_evidence + semantic_evidence
  -> trace.json
  -> WorkflowValidator
  -> lumiagent show
```

This is the enhanced semantic trace path. Transcript enrichment is best-effort.

### 5.3 Synthetic Fixture Flow

```text
synthetic normalized events
  -> TraceWriter
  -> AgentRun fixture
  -> validator tests
  -> viewer tests
```

Synthetic fixtures provide stable coverage for the formal taxonomy and do not require Claude Code to run locally.

## 6. Mapping Rules

Tool names map to semantic Coding Agent conventions:

```text
Grep / Glob / search tools
  -> file_search

Read
  -> file_read

Edit / Write / patch
  -> code_edit

Bash pytest / ruff / mypy / npm test
  -> test_run or verification

Bash git diff
  -> git_diff

Bash git status / git log
  -> shell_command with metadata.purpose = git_review

Generic Bash
  -> shell_command

Tool or command failure
  -> error_observed

Follow-up retry or fix after error
  -> failure_recovery

Permission prompt / approval result
  -> permission_request / approval_decision

Assistant planning or task summary
  -> task_understanding

Assistant interpretation of tool or test result
  -> result_interpretation

Final assistant message
  -> final_response
```

Raw tool name, arguments, outputs, and summaries are preserved in `action_evidence` artifacts or events. Semantic classification is represented through metadata, such as `metadata.type = "code_edit"`.

## 7. Recommended Trace Shape

Successful trace:

```text
coding_agent_run [success]
├── user_prompt
├── task_understanding
├── context_gathering
│   ├── file_search
│   └── file_read
├── code_edit
├── verification
│   ├── shell_command
│   └── test_run
├── git_diff
├── result_interpretation
├── final_response
└── workflow_check
```

Failure and recovery trace:

```text
coding_agent_run [success|error]
├── user_prompt
├── task_understanding
├── context_gathering
│   └── file_read
├── code_edit
├── verification
│   └── test_run [error]
├── error_observed
├── failure_recovery
│   ├── file_read
│   ├── code_edit
│   └── test_run [success]
├── result_interpretation
├── final_response
└── workflow_check
```

Permission and risk trace:

```text
coding_agent_run [error]
├── shell_command
├── permission_request
├── approval_decision [denied]
├── error_observed
├── final_response
└── workflow_check
```

## 8. Event and Evidence Schemas

### 8.1 Claude Code Hook Event Format

Each line in `.lumiagent/sessions/<session-id>/events.jsonl` is a LumiAgent-owned JSON object:

```json
{
  "schema_version": "coding_hook_event.v1",
  "event_id": "evt_001",
  "session_id": "session_abc",
  "sequence": 1,
  "timestamp": "2026-05-28T10:00:00Z",
  "source": "claude_code_hook",
  "hook_name": "PostToolUse",
  "tool_name": "Read",
  "phase": "tool_result",
  "working_directory": "D:/Projects/github/lumiagent",
  "payload": {},
  "safety": {
    "redaction_state": "raw"
  }
}
```

Important fields:

- `schema_version`: hook event format version;
- `event_id`: LumiAgent event ID;
- `session_id`: session identifier;
- `sequence`: monotonically increasing sequence within the session;
- `timestamp`: hook timestamp;
- `source`: `claude_code_hook`;
- `hook_name`: Claude Code hook name;
- `tool_name`: tool name when available;
- `phase`: `tool_request`, `tool_result`, `permission_request`, or `error`;
- `payload`: source-specific content;
- `safety.redaction_state`: `raw` or `sanitized`.

### 8.2 Normalized Coding Event Format

Normalized events are source-independent converter inputs to TraceWriter:

```json
{
  "event_id": "coding_evt_001",
  "source_event_ids": ["evt_001", "evt_002"],
  "session_id": "session_abc",
  "sequence": 1,
  "timestamp": "2026-05-28T10:00:00Z",
  "convention": "test_run",
  "status": "success",
  "parent_convention": "verification",
  "name": "Run pytest",
  "action_evidence": {
    "tool_name": "Bash",
    "arguments": {
      "command": "python -m pytest -v"
    },
    "duration_ms": 1234,
    "exit_code": 0,
    "stdout_summary": "98 passed",
    "stderr_summary": "",
    "output_truncated": false
  },
  "semantic_evidence": null,
  "metadata": {
    "classification_reason": "Bash command matched pytest test command pattern"
  }
}
```

Normalized event categories:

- `CodingActionEvent`;
- `CodingSemanticEvent`;
- `CodingWorkflowFinding`.

### 8.3 Transcript Enrichment Format

Transcript enrichment produces semantic items:

```json
{
  "schema_version": "coding_transcript_enrichment.v1",
  "session_id": "session_abc",
  "source": "claude_code_transcript",
  "source_path": "redacted-or-local-only",
  "status": "success",
  "items": [
    {
      "item_id": "sem_001",
      "timestamp": "2026-05-28T10:00:00Z",
      "convention": "user_prompt",
      "role": "user",
      "content_summary": "Fix failing import error in local package tests.",
      "content": "Fix failing import error in local package tests.",
      "confidence": "high"
    }
  ],
  "warnings": []
}
```

Unsupported enrichment returns an empty item list with warnings and must not fail hooks-only conversion.

### 8.4 Span Metadata

Coding Agent spans should include stable metadata:

```json
{
  "type": "test_run",
  "domain": "coding_agent",
  "source": "claude_code_hook",
  "source_event_ids": ["evt_001", "evt_002"],
  "evidence_types": ["action_evidence"],
  "classification": {
    "strategy": "rule",
    "reason": "Bash command matched pytest pattern"
  }
}
```

Semantic span example:

```json
{
  "type": "task_understanding",
  "domain": "coding_agent",
  "source": "transcript_enrichment",
  "source_item_ids": ["sem_002"],
  "evidence_types": ["semantic_evidence"],
  "confidence": "medium"
}
```

### 8.5 Evidence Artifacts

Action evidence artifact:

```json
{
  "artifact_type": "coding_action_evidence",
  "schema_version": "coding_action_evidence.v1",
  "source": "claude_code_hook",
  "tool_name": "Bash",
  "arguments": {
    "command": "python -m pytest -v"
  },
  "result": {
    "status": "success",
    "exit_code": 0,
    "duration_ms": 1234,
    "stdout_summary": "98 passed",
    "stderr_summary": "",
    "output_truncated": false
  },
  "safety": {
    "redaction_state": "raw"
  }
}
```

Semantic evidence artifact:

```json
{
  "artifact_type": "coding_semantic_evidence",
  "schema_version": "coding_semantic_evidence.v1",
  "source": "transcript_enrichment",
  "convention": "task_understanding",
  "role": "assistant",
  "content_summary": "Need to inspect package layout and run tests.",
  "content": "Need to inspect package layout and run tests.",
  "confidence": "medium",
  "safety": {
    "redaction_state": "raw"
  }
}
```

Workflow finding artifact:

```json
{
  "artifact_type": "coding_workflow_finding",
  "schema_version": "coding_workflow_finding.v1",
  "rule_id": "code_edit_requires_verification",
  "status": "failed",
  "severity": "warning",
  "summary": "Code was edited without a later test or verification span.",
  "evidence_span_ids": ["span_code_edit_001"],
  "expected": "A code_edit span should be followed by test_run or verification.",
  "actual": "final_response occurred after code_edit without verification.",
  "confidence": "high"
}
```

## 9. TraceWriter, Converter, and Validator Behavior

### 9.1 TraceWriter

Recommended implementation:

```text
BuilderTraceWriter
```

It wraps `TraceBuilder` and supports:

- `start_run()`;
- `start_span()`;
- `end_span()`;
- `add_event()`;
- `add_artifact()`;
- `flush()`.

It should maintain enough state to support incremental span creation and deterministic parent assignment. It is not a persistent writer.

### 9.2 Converter

Recommended component:

```text
ClaudeCodeTraceConverter
```

Pipeline:

```text
read hook events
  -> validate event schema
  -> optional sanitize raw events
  -> optional transcript enrichment
  -> normalize hook events into CodingActionEvent
  -> normalize transcript items into CodingSemanticEvent
  -> merge by timestamp / sequence
  -> write spans/artifacts through TraceWriter
  -> run WorkflowValidator
  -> append workflow_check findings
  -> flush AgentRun
```

Ordering rules:

1. Use hook `sequence` first.
2. Use timestamps for transcript enrichment when available.
3. If transcript timestamps are missing:
   - place `user_prompt` before first action;
   - place `task_understanding` before first action when possible;
   - place `result_interpretation` after a related action span when relation is clear;
   - place `final_response` after the last action.
4. Preserve source IDs for debugging.

Request/result pairing should prefer stable IDs if available, then sequence adjacency, then conservative tool-name/timestamp matching. Unpaired events must be preserved with pairing metadata rather than dropped.

### 9.3 Normalization

Command classification should be rule-based:

```text
pytest / python -m pytest / npm test / pnpm test / yarn test
  -> test_run

ruff / mypy / pyright / eslint / tsc
  -> verification or test_run subtype

git diff
  -> git_diff

git status / git log
  -> shell_command with metadata.purpose = git_review

unknown command
  -> shell_command
```

File tool classification:

```text
Glob / Grep / file search tools -> file_search
Read -> file_read
Edit / Write / patch -> code_edit
```

Permission events map to `permission_request` and `approval_decision` with risk metadata when available.

### 9.4 Workflow Validator

Validator consumes `AgentRun` and emits structured workflow findings.

Initial rules:

```text
code_edit_requires_verification
failed_test_requires_recovery
failed_command_requires_recovery
permission_denied_blocks_action
final_response_after_unresolved_error
```

Aggregate status:

```text
pass
warning
error
not_applicable
```

Findings should be stored under a `workflow_check` span as structured artifacts. Phase 3 does not store them as full Diagnosis records by default.

## 10. CLI Behavior

### 10.1 `lumiagent setup claude-code`

Responsibilities:

- locate or create project `.claude/settings.json`;
- merge LumiAgent hooks without deleting existing hooks;
- configure hooks to write `.lumiagent/sessions/<session-id>/events.jsonl`;
- print configured hook summary;
- warn or preserve backups on conflicts.

Safety requirements:

- do not overwrite unrelated user hooks;
- do not store secrets in settings;
- make all changes explicit.

### 10.2 `lumiagent trace <session-id> -o trace.json`

Responsibilities:

- read `.lumiagent/sessions/<session-id>/events.jsonl`;
- optionally find or accept transcript input;
- run converter and validator;
- write trace JSON;
- print trace summary.

Example summary:

```text
Trace written: trace.json
Spans: 18
Workflow checks: warning (1 finding)
Transcript enrichment: success
```

### 10.3 `lumiagent show <trace.json>`

For Coding Agent traces, show:

```text
Run: <name>
Status: success

Semantic Summary:
  User prompt: ...
  Task understanding: ...
  Final response: ...

Span Tree:
- Coding Agent Run [success]
  - User Prompt
  - Context Gathering
    - File Search
    - File Read
  - Code Edit
  - Verification
    - Test Run
  - Final Response
  - Workflow Check [pass]

Workflow Checks:
  status: pass
```

### 10.4 `lumiagent show <trace.json> --checks`

Shows detailed workflow findings:

```text
Workflow Checks Detail:
- rule: code_edit_requires_verification
  status: failed
  severity: warning
  evidence spans: span_code_edit_001
  expected: code_edit should be followed by test_run or verification
  actual: no later verification span found
```

## 11. Fixtures and Testing

### 11.1 Unit Tests

Required coverage:

- Coding conventions and schemas;
- `BuilderTraceWriter` behavior;
- span-level serialization;
- Claude Code hook event schema and JSONL reader;
- transcript enrichment success, missing, unsupported, and failure cases;
- normalizer tool mapping;
- converter request/result pairing;
- workflow validator rules;
- viewer output.

Recommended test paths:

```text
tests/adapters/coding/test_conventions.py
tests/adapters/coding/test_schemas.py
tests/adapters/coding/test_normalizer.py
tests/adapters/coding/test_validator.py
tests/adapters/coding/test_viewer.py
tests/adapters/claude_code/test_events.py
tests/adapters/claude_code/test_hooks_reader.py
tests/adapters/claude_code/test_transcript.py
tests/adapters/claude_code/test_converter.py
tests/adapters/claude_code/test_converter_pairing.py
tests/tracing/test_writer.py
tests/tracing/test_span_serialization.py
tests/test_cli_coding_trace.py
```

### 11.2 Synthetic Fixtures

Committed synthetic fixtures:

```text
tests/adapters/coding/fixtures/coding_trace_success.json
tests/adapters/coding/fixtures/coding_trace_missing_verification.json
tests/adapters/coding/fixtures/coding_trace_failed_test_recovered.json
tests/adapters/coding/fixtures/coding_trace_permission_denied.json
```

Synthetic fixtures are stable, deterministic, and safe to commit.

### 11.3 Real Capture Fixtures

Local-only raw data:

```text
.lumiagent/sessions/<session-id>/events.jsonl
.lumiagent/sessions/<session-id>/transcript.*
.lumiagent/traces/<session-id>-raw.json
```

Committed sanitized real fixture:

```text
tests/adapters/claude_code/fixtures/real_session_sanitized_trace.json
```

Optional committed sanitized source events:

```text
tests/adapters/claude_code/fixtures/real_session_sanitized_events.jsonl
```

Sanitized fixtures must preserve span shape, ordering, conventions, evidence shape, statuses, semantic summaries, and workflow findings. They must remove private code, credentials, machine-specific paths, sensitive prompts, and unnecessary raw output.

## 12. Verification Plan

### 12.1 Real Claude Code Verification

Setup:

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli setup claude-code
```

Run Claude Code normally on a small safe task. Expected output:

```text
.lumiagent/sessions/<session-id>/events.jsonl
```

Convert:

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli trace <session-id> -o ".lumiagent/traces/<session-id>-raw.json"
```

Show:

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli show ".lumiagent/traces/<session-id>-raw.json"
python -m lumiagent.cli show ".lumiagent/traces/<session-id>-raw.json" --checks
```

### 12.2 Automated Verification Commands

Use the project verification commands expanded for new modules:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture tests/tracing tests/adapters tests/capture
python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture
```

## 13. Implementation Staging

### Stage 1: Coding Agent Trace Conventions and Schemas

Deliver conventions, normalized event schemas, evidence schemas, and workflow finding schema.

Acceptance:

- conventions importable and stable;
- evidence payloads constructible and serializable;
- no Claude Code-specific fields in Trace Core.

### Stage 2: TraceWriter Minimal Implementation

Deliver `BuilderTraceWriter` and writer tests.

Acceptance:

- incremental run/span/event/artifact creation works;
- `flush()` returns valid `AgentRun`;
- MCP mapper migration is not required.

### Stage 3: Claude Code Events and Converter

Deliver hook event schema, JSONL reader, normalizer, converter, and hooks-only conversion tests.

Acceptance:

- hooks-only events convert to valid `AgentRun`;
- major tools map to formal conventions;
- converter uses TraceWriter.

### Stage 4: Transcript Enrichment and Sanitization

Deliver transcript enrichment and sanitization hook.

Acceptance:

- semantic fields are extracted when available;
- missing or unsupported transcript does not block conversion;
- sanitized fixtures preserve structure without leaking sensitive content.

### Stage 5: Workflow Validator and Viewer Integration

Deliver validator, initial rules, workflow_check artifact, and show output integration.

Acceptance:

- initial rules produce structured findings;
- `lumiagent show` displays semantic summary and workflow checks;
- `lumiagent show --checks` displays detailed findings.

### Stage 6: Real Capture Verification and Technical Report

Deliver setup command, trace command, real verification, sanitized fixture, and Chinese report.

Acceptance:

- real Claude Code session captured and converted;
- trace viewable in CLI;
- tests and static checks pass;
- technical report is written.

## 14. Risks and Mitigations

### 14.1 Hook Payload Differences

Risk: Claude Code hook payloads may differ by environment or version.

Mitigation: store only available stable fields, degrade gracefully on missing fields, preserve source IDs, and document actual payload coverage in the technical report.

### 14.2 Transcript Instability

Risk: transcript format may change.

Mitigation: keep enrichment best-effort and isolated; hooks-only trace remains required and valid; do not encode transcript internals into Trace Core.

### 14.3 Sensitive Data in Real Traces

Risk: real traces may contain private code, paths, credentials, or prompts.

Mitigation: keep raw data local; commit only sanitized/minimized fixtures; include sanitizer hook and report redaction strategy.

### 14.4 Validator False Positives

Risk: users may interpret workflow checks as complete diagnosis.

Mitigation: name them Workflow Checks or Trace Review Findings, limit to deterministic high-confidence rules, and leave semantic diagnosis to Phase 4.

### 14.5 Hook Setup Configuration Risk

Risk: setup may overwrite existing Claude Code hooks.

Mitigation: merge only LumiAgent-managed entries, preserve unknown settings, warn on conflict, and test merge behavior.

### 14.6 Scope Creep

Risk: Phase 3 could expand into dashboard, SDK, proxy, or diagnosis engine.

Mitigation: keep UI to CLI trace review, keep Diagnosis for Phase 4, keep replay/view models for Phase 5, and keep SDK/proxy for later phases.

## 15. Open Questions for Implementation Planning

These do not block this specification but should be resolved in the implementation plan:

1. Whether the minimal writer file should be named `builder_writer.py`, `memory_writer.py`, or kept in `writer.py`.
2. Whether `lumiagent trace` should accept `--transcript-path`.
3. Whether fixture sanitization should be a public `--sanitize` option or an internal helper.
4. Whether workflow findings should also add root summary events in addition to `workflow_check` artifacts.
5. Whether lint/typecheck commands are `verification` or `test_run` subtypes.
6. Whether `git status` and `git log` should remain `shell_command` with `purpose=git_review`.
7. Which small real task should produce the sanitized Claude Code fixture.

## 16. Technical Report Requirement

After implementation, write:

```text
docs/reports/coding-agent-trace-model-technical-report.zh-CN.md
```

The report must cover:

- Phase 3 purpose and scope;
- why generic semantic Coding Agent trace is the core;
- why Claude Code hooks are the first adapter but not the model source;
- why transcript enrichment is best-effort;
- why TraceWriter is limited to incremental coding capture;
- why `McpTraceMapper` is not refactored;
- schema and artifact design;
- validator rules and boundaries;
- fixture sanitization policy;
- automated verification results;
- real Claude Code capture verification result;
- risks and follow-up recommendations.

## 17. Acceptance Criteria

Phase 3 is complete when:

1. Unified Coding Agent trace conventions express a workflow from user request to final response.
2. The stable conventions listed in Section 2.1 can be represented and serialized.
3. Claude Code hooks write LumiAgent-owned `events.jsonl` files.
4. `lumiagent trace <session-id> -o trace.json` converts hooks events to a valid `AgentRun`.
5. Minimal transcript enrichment supplements semantic evidence when available.
6. Hooks-only trace remains valid when transcript is unavailable or unsupported.
7. The hooks converter uses `TraceWriter`.
8. Phase 2b `McpTraceMapper` is not required to migrate.
9. Workflow validator emits deterministic, high-confidence structured findings.
10. `lumiagent show <trace.json>` displays span tree, semantic summary, and workflow checks.
11. `lumiagent show <trace.json> --checks` displays detailed workflow findings.
12. Synthetic Coding Agent fixtures are committed and used in tests.
13. A real Claude Code session is locally captured and converted.
14. A sanitized/minimized real fixture is committed without sensitive content.
15. Required pytest, ruff, and mypy commands pass.
16. The Chinese technical report is written.
