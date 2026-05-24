# CLAUDE.md

This file provides project-level guidance for AI coding assistants working on LumiAgent.

## Project Positioning

LumiAgent is a general Agent Trace / Eval Core that models LLM, Tool, RAG, Memory, Evaluator, Fallback, and Error steps as a nested Span Tree. Each Agent Run should be structured, replayable, evaluable, and diagnosable.

The first application focuses on Coding Agents and MCP Tool Chains. LumiAgent captures file search, code reading, code edits, command execution, test verification, MCP tool discovery, tool calls, argument generation, and tool results to diagnose context gaps, tool misuse, argument errors, result misinterpretation, insufficient verification, failure recovery issues, and risk-control problems.

## Current Product Focus

Prioritize the following product line:

1. General Agent Trace / Eval Core
2. Span Tree based trace model
3. Coding Agent trace capture and replay
4. MCP Tool Chain observability
5. Agent evaluation and diagnosis
6. Workflow optimization for Coding Agents

## Non-Goals

Do not turn LumiAgent into any of the following unless the project spec is explicitly updated:

- A generic LangSmith/Langfuse clone
- A general LLM observability dashboard
- A prompt management platform
- A generic RAG evaluation platform
- A large all-purpose Agent framework
- A generic multi-agent orchestration framework

These capabilities may appear as supporting infrastructure, but they are not the main product direction.

## Implementation Rules

All implementation work must follow these rules:

1. Requirement specification first
   - Define requirements, scope, non-goals, and acceptance criteria before changing code.
   - Code changes must map back to the agreed specification.

2. Architecture first
   - Keep module boundaries clear.
   - Choose patterns that preserve extensibility and compatibility.
   - Prefer small, composable units with explicit interfaces.

3. Staged acceptance
   - Every implementation stage must have clear deliverables and acceptance criteria.
   - Avoid open-ended work that can drift away from the core positioning.

4. Testing throughout
   - Every stage must include tests or executable verification.
   - Do not claim completion without running the relevant checks.
   - Prefer realistic usage tests over purely superficial checks.

## Architecture Principles

- Treat traces as first-class product data.
- Model Agent execution as Runs, Spans, Events, Artifacts, Evaluations, and Diagnoses.
- Keep the core trace model framework-agnostic.
- Keep Coding Agent and MCP support as adapters on top of the core model.
- Avoid coupling the core to Claude Code, LangChain, LangGraph, or any single Agent framework.
- Design for future ingestion from SDKs, hooks, MCP proxies, CLI wrappers, and transcript importers.

## Expected MVP Direction

The MVP should prioritize:

1. Trace Schema / Span Tree Core
2. MCP Tool Chain capture model
3. Coding Agent trace model
4. Trace Replay data flow
5. Evaluation and diagnosis model
6. Minimal runnable examples and tests

## Quality Bar

Before marking work complete:

- Requirements are documented.
- Architecture decisions are reflected in code structure.
- Tests or verification commands have passed.
- The result can be explained through the project positioning.
- The implementation does not expand scope beyond the current stage.
