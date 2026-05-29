# Coding Agent Trace Model Design

This design is the approved Phase 3 requirements and architecture specification for LumiAgent.

Canonical specification:

```text
docs/specs/coding-agent-trace-model.md
```

Summary:

Phase 3 builds a Generic Semantic Coding Trace Core and uses Claude Code hooks plus minimal transcript enrichment as the first real Capture Adapter. The phase proves that a coding workflow can be captured, normalized, converted, pre-checked, and reviewed.

Key decisions:

- The Coding Agent trace model is framework-agnostic and not tied to Claude Code internals.
- Claude Code hooks provide stable action evidence.
- Transcript enrichment provides best-effort semantic evidence.
- TraceWriter is used only for incremental Coding Agent hooks capture in Phase 3.
- Phase 2b `McpTraceMapper` remains unchanged.
- Workflow validator is deterministic, structured, high-confidence, and shown as trace review findings rather than full Evaluation/Diagnosis.
- Synthetic fixtures are committed for stable tests; raw real Claude Code capture data stays local; only sanitized/minimized real fixtures are committed.
