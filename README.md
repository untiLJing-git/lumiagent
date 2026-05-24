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

Implementation report:

- [`docs/reports/trace-core-mvp-technical-report.zh-CN.md`](docs/reports/trace-core-mvp-technical-report.zh-CN.md)

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

```text
AgentRun
├── root_spans[]
│   └── Span
│       ├── events[]
│       ├── artifacts[]
│       └── children[]
├── evaluations[]
└── diagnoses[]
```

The trace core is intentionally independent from any single agent framework. Coding Agent support, MCP Tool Chain capture, SDK hooks, CLI wrappers, and transcript importers should be built as adapters on top of the core model.

## Roadmap

- [x] Trace Schema / Span Tree Core
- [ ] MCP Tool Chain capture model
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
└── tracing/
    ├── __init__.py
    ├── builder.py
    ├── enums.py
    ├── models.py
    ├── serializer.py
    └── validator.py

tests/tracing/
├── fixtures/
├── test_builder.py
├── test_models.py
├── test_serializer.py
└── test_validator.py

docs/reports/
└── trace-core-mvp-technical-report.zh-CN.md
```

## Installation

```bash
pip install -e ".[dev]"
```

Python 3.11+ is required.

## Verification

```bash
python -m pytest -v
python -m ruff check src/lumiagent/tracing tests/tracing
python -m mypy src/lumiagent/tracing
```

If the package is not installed in editable mode, run the checks with the local source path:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing tests/tracing
python -m mypy src/lumiagent/tracing
```

Current Trace Core MVP validation result:

```text
18 passed
All checks passed
Success: no issues found in 6 source files
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
