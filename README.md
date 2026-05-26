# LumiAgent

[简体中文](README.zh-CN.md)

LumiAgent is an Agent Trace / Eval Core for recording, replaying, evaluating, and diagnosing agent runs.

The current MVP focuses on a framework-agnostic trace data foundation: an agent run is represented as a nested Span Tree with events, artifacts, evaluations, and diagnoses. The first application direction is observability and diagnosis for Coding Agents and MCP Tool Chains.

## Why LumiAgent

Agent systems are becoming more tool-heavy and workflow-heavy, but many failures are still hard to explain:

- Was the right context retrieved?
- Did the agent call the right tool?
- Were tool arguments generated correctly?
- Did the agent misread the tool result?
- Was the verification step sufficient?
- Which span provides evidence for an evaluation or diagnosis?

LumiAgent starts from the data foundation for answering these questions: a structured, replayable, evaluable, and diagnosable trace model.

## Current Status

**Stage 1: Trace Core MVP — completed**

Implemented capabilities:

- Agent run model with nested Span Tree
- Span events and artifacts
- Evaluation and diagnosis records with evidence span references
- Stable enum values for run, span, event, artifact, target, and severity types
- JSON/dict serialization and round-trip loading
- Structural validation for span IDs, parent-child links, target references, and evidence spans
- Convenience `TraceBuilder` API
- Generic Agent and Coding Agent trace fixtures

**Stage 2: MCP Tool Chain Model — completed**

Implemented capabilities:

- MCP adapter/convention layer under `src/lumiagent/adapters/mcp/`
- Stable MCP span and artifact `metadata.type` conventions
- `McpFailureType` taxonomy outside the generic Trace Core
- Lightweight MCP evidence schemas for schema snapshots, tool calls, execution summaries, failures, and result consumption
- Builder helpers for MCP tool-chain spans, artifacts, results, and failure evidence
- Successful and failed MCP trace fixtures covering `argument_invalid`, `tool_execution_failed`, and `result_misinterpreted`

Product value:

- Preserves structured evidence for how an Agent discovers tools, sees schemas, generates arguments, executes MCP tools, and consumes results.
- Keeps MCP as an adapter evidence layer so Phase 3 Coding Agent Trace and Phase 4 Evaluation / Diagnosis can consume stable evidence without polluting the Core model.

Specifications and reports:

- [`docs/specs/mcp-tool-chain-model.md`](docs/specs/mcp-tool-chain-model.md)
- [`docs/reports/trace-core-mvp-technical-report.zh-CN.md`](docs/reports/trace-core-mvp-technical-report.zh-CN.md)
- [`docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md`](docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md)

## Quick Example

```python
from lumiagent.tracing import SpanKind, TraceBuilder, to_json

builder = TraceBuilder(name="coding agent run", input_value={"task": "fix failing test"})

agent_span = builder.start_span("Coding Agent", kind=SpanKind.AGENT)
search_span = builder.start_span(
    "Search files",
    kind=SpanKind.TOOL,
    parent_span_id=agent_span,
    metadata={"operation": "file_search"},
)
builder.end_span(search_span, output={"matches": ["src/lumiagent/tracing/models.py"]})
builder.end_span(agent_span, output={"result": "trace captured"})

run = builder.build(output={"status": "done"})
print(to_json(run))
```

## Architecture

![Trace Core Model](docs/assets/trace-core-model.svg)

Mermaid source: [`docs/diagrams/trace-core-model.mmd`](docs/diagrams/trace-core-model.mmd)

![MCP Tool Chain Evidence Layer](docs/assets/mcp-tool-chain-evidence-layer.svg)

Mermaid source: [`docs/diagrams/mcp-tool-chain-evidence-layer.mmd`](docs/diagrams/mcp-tool-chain-evidence-layer.mmd)

The trace core is intentionally independent from any single agent framework. Coding Agent support, MCP Tool Chain capture, SDK hooks, CLI wrappers, and transcript importers should be built as adapters on top of the core model.

The MCP Tool Chain layer is an adapter evidence layer: it records tool discovery, schema snapshots, argument generation, permission, execution results, failure evidence, and result consumption without adding MCP-specific fields to the Trace Core.

## Roadmap

- [x] Trace Schema / Span Tree Core
- [x] MCP Tool Chain evidence model
- [ ] Coding Agent trace model
- [ ] Trace Replay data flow
- [ ] Evaluation and diagnosis engine
- [ ] Minimal runnable examples and tests

Non-goals for the current MVP:

- Generic LangSmith/Langfuse clone
- Prompt management platform
- Generic RAG evaluation platform
- Full multi-agent orchestration framework

## Project Structure

```text
src/lumiagent/
├── adapters/
│   └── mcp/
│       ├── __init__.py
│       ├── builder.py
│       ├── conventions.py
│       ├── schemas.py
│       └── taxonomy.py
└── tracing/
    ├── __init__.py
    ├── builder.py
    ├── enums.py
    ├── models.py
    ├── serializer.py
    └── validator.py

tests/
├── adapters/mcp/
│   ├── fixtures/
│   ├── test_fixtures.py
│   ├── test_mcp_builder.py
│   ├── test_schemas.py
│   └── test_taxonomy.py
└── tracing/
    ├── fixtures/
    ├── test_builder.py
    ├── test_models.py
    ├── test_serializer.py
    └── test_validator.py

docs/
├── reports/
│   ├── trace-core-mvp-technical-report.zh-CN.md
│   └── mcp-tool-chain-model-technical-report.zh-CN.md
└── specs/
    └── mcp-tool-chain-model.md
```

## Installation

```bash
pip install -e ".[dev]"
```

Python 3.11+ is required.

## Verification

```bash
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

If the package is not installed in editable mode, run the checks with the local source path:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

## Tech Stack

| Area | Technology |
| --- | --- |
| Language | Python 3.11+ |
| Data Model | Pydantic v2 |
| Testing | pytest |
| Linting | ruff |
| Type Checking | mypy |

## License

MIT
