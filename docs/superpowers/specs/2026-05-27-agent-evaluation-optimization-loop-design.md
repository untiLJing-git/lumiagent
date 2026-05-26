# Agent Evaluation and Optimization Loop Design

Date: 2026-05-27

## 1. Purpose

This document defines the product loop that should guide LumiAgent's next design work:

```text
run tasks → capture traces → diagnose failures → review evidence → apply improvements → compare reruns
```

The goal is to turn agent evaluation from a final score into an executable path to improvement. A benchmark score can show whether an agent succeeded. LumiAgent should explain how the run unfolded, where the failure emerged, what evidence supports the diagnosis, which improvement is most likely to help, and whether a rerun actually improved behavior.

This document is a standalone design note. It does not change the current roadmap by itself.

## 2. Core Product Value

LumiAgent should not stop at trace collection or benchmark scoring. Its core value is the closed-loop process of evaluating, diagnosing, reviewing, improving, and validating agent behavior.

The loop has six steps:

1. **Run tasks** — execute a benchmark task set against an agent under controlled conditions.
2. **Capture traces** — record each run as a structured AgentRun trace with spans, artifacts, evaluations, and diagnoses.
3. **Diagnose failures** — use Diagnosis Agent and rule-based checks to identify failure patterns and evidence spans.
4. **Review evidence** — help humans inspect the trace, diagnosis, and supporting spans through CLI/TUI first, UI later.
5. **Apply improvements** — produce concrete, reviewable suggestions at prompt, config, tool schema, workflow, or knowledge levels.
6. **Compare reruns** — rerun the same task set and compare pass/fail rates, failure patterns, and trace differences.

Evaluation is not the endpoint. It becomes the operating system for improving agent behavior.

## 3. Minimal MVP Path

The minimal MVP should use a local, controlled benchmark and LumiAgent's own agent infrastructure. It should not start with SWE-bench or external agents.

### 3.1 Why start locally

A local benchmark is the shortest path to validating the loop because:

- task setup is deterministic and cheap;
- repositories are small and easy to inspect;
- pass/fail can be verified with local test commands;
- LumiAgent's own ReActEngine can emit traces directly;
- Diagnosis Agent can be calibrated against known expected failure modes;
- no external agent integration is required for the first loop.

The purpose of the MVP is not to prove LumiAgent has the strongest coding agent. The purpose is to prove LumiAgent can evaluate, diagnose, explain, and improve an agent workflow.

### 3.2 MVP components

| Component | MVP scope | Out of scope |
|-----------|-----------|--------------|
| Local Coding Benchmark | 12 representative local coding cases | SWE-bench, large repos, public leaderboard |
| LumiAgent Coding Agent | ReActEngine + existing tool registry | Competing with Claude Code capability |
| Trace Capture | Built-in TraceWriter / TraceBuilder integration | External hooks or proxy capture |
| Verification | Per-case `test_command` pass/fail | Human success judgment |
| Diagnosis Agent | Failure pattern analysis and suggested fixes | Fully automatic agent modification |
| Human Review | CLI/TUI evidence review | Full Web UI |
| Rerun Diff | Compare before/after experiments | Long-term benchmark infrastructure |

### 3.3 Local benchmark structure

Recommended directory shape:

```text
eval_sets/coding_local_mvp/
├── manifest.json
└── cases/
    └── import_error_001/
        ├── repo/
        ├── task.md
        ├── test_command.txt
        ├── metadata.json
        └── expected_failure_modes.json
```

Each case should include:

- `repo/` — a small repository snapshot with a known bug or task;
- `task.md` — natural language task instruction for the agent;
- `test_command.txt` — command used to verify success;
- `metadata.json` — difficulty, required skills, expected tools, tags;
- `expected_failure_modes.json` — likely failure modes used to calibrate Diagnosis Agent.

### 3.4 Representative case set

Start with 12 cases:

| Category | Count | Capability tested | Likely failures exposed |
|----------|-------|-------------------|--------------------------|
| Import / path error | 2 | read stack traces, locate files | shallow context gathering |
| Unit test failure | 2 | run tests, understand assertions | missing verification, result misread |
| Edge case bug | 2 | handle boundary conditions | happy-path-only fixes |
| Multi-file change | 2 | understand cross-file relationships | incomplete edits |
| Tool-use heavy task | 2 | search/read/edit/test chain | tool selection or argument errors |
| Regression risk task | 2 | preserve old behavior | over-editing, insufficient regression checks |

This set is small enough for iteration but broad enough to expose common coding-agent failure patterns.

## 4. Claude Code Comparison Path

Claude Code should not be part of the first MVP loop. It should be the next comparison path after the local loop works.

### 4.1 Comparison flow

```text
same coding_local_mvp task set
        │
        ├── LumiAgent Coding Agent Runner
        │      └── built-in TraceWriter → trace.json
        │
        └── Claude Code Runner
               └── hooks CaptureStrategy → trace.json

LumiAgent Experiment A vs Experiment B
        ↓
pass/fail comparison
        ↓
failure-pattern comparison
        ↓
trace diff and diagnosis review
```

### 4.2 Why this is feasible

- The task set is local and controlled.
- Claude Code hooks provide a stable capture point for tool calls and results.
- Both agents can be normalized into AgentRun traces.
- Diagnosis Agent, trace viewer, and experiment diff can operate on the same output format.
- Trace granularity does not need to be identical; the shared layer is span taxonomy and failure taxonomy.

### 4.3 Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Hooks may not capture full reasoning or user messages | Start with tool calls/results; transcript enrichment is optional |
| Claude Code automation may affect local files | Run each case in an isolated temp copy |
| Different agents produce different trace granularity | Normalize to shared span and failure taxonomies, not identical event streams |
| Comparison becomes a product claim about superiority | Frame it as failure-mode comparison, not a leaderboard |

## 5. Failure Diagnosis to Improvement

The loop should not claim full automatic optimization. It should produce concrete, reviewable, and verifiable suggestions.

### 5.1 Suggested fix structure

Diagnosis Agent should aggregate failure patterns and produce suggestions like:

```json
{
  "failure_pattern": "insufficient_verification",
  "occurrence": "5/12 cases",
  "evidence_summary": "code_edit span was not followed by test_run span",
  "representative_spans": ["span_123", "span_456"],
  "suggested_fixes": [
    {
      "level": "prompt",
      "action": "Add instruction: after every code edit, run the relevant test command before final answer.",
      "expected_impact": "high",
      "auto_applicable": true
    },
    {
      "level": "workflow",
      "action": "Add a post-edit verification gate in the agent loop.",
      "expected_impact": "high",
      "auto_applicable": false
    }
  ]
}
```

### 5.2 Improvement levels

| Level | Example | MVP support |
|-------|---------|-------------|
| Prompt | Add instruction to run tests after edits | Generate suggestion; human applies |
| Config | Increase search results or max iterations | Generate suggestion; human applies |
| Tool Schema | Improve tool descriptions and parameter docs | Suggest only |
| Workflow | Add mandatory verification gate | Suggest only |
| Knowledge | Add failure pattern to knowledge base | Future phase |

The MVP should support prompt/config suggestions well. Workflow, tool schema, and knowledge suggestions can be produced but should not be automatically applied.

### 5.3 Verification after improvement

After applying a suggestion, rerun the same benchmark and compare:

- pass/fail rate;
- failure pattern frequency;
- representative trace differences;
- whether the target failure mode decreased.

This makes optimization evidence-based rather than anecdotal.

## 6. Human Review and Visualization

The UI/CLI layer exists to help humans inspect whether Diagnosis Agent's conclusions are trustworthy.

### 6.1 Minimal review views

| View | Question answered |
|------|-------------------|
| Experiment Overview | How did this benchmark run perform overall? |
| Case Detail | Why did this case fail? |
| Span Tree / Timeline | What did the agent actually do? |
| Evidence Panel | Which spans support the diagnosis? |
| Suggestion Panel | What should be changed, and at what level? |
| Rerun Diff | Did the improvement actually reduce the failure mode? |

### 6.2 MVP interface

Start with CLI/TUI commands:

```bash
lumiagent experiment show exp_001
lumiagent case show exp_001 import_error_001
lumiagent trace show trace.json
lumiagent experiment diff exp_before exp_after
```

A later Web UI should consume the same view models rather than redefine the product semantics.

### 6.3 Annotation feedback

Human reviewers should eventually be able to mark:

- diagnosis correct / incorrect;
- failure type correct / incorrect;
- evidence span sufficient / insufficient;
- suggested fix actionable / not actionable.

Annotations feed the future expert knowledge base and diagnosis evaluation set.

## 7. Feasibility Assessment

### 7.1 Minimal MVP: high feasibility

Reasons:

- local cases are deterministic;
- existing ReActEngine, ToolRegistry, TraceBuilder, and EvaluationSuite provide useful starting points;
- trace capture for the built-in agent is controllable;
- pass/fail verification can rely on test commands;
- Diagnosis Agent can start with rules plus LLM reasoning;
- UI can start as CLI/TUI.

Main risks:

- the built-in agent may be weak on complex tasks;
- Diagnosis Agent may overfit or hallucinate diagnoses;
- UI scope can expand too early.

Mitigations:

- keep the first benchmark to 12 small cases;
- include expected failure modes and human annotations;
- keep Web UI out of the MVP and use CLI/TUI first.

### 7.2 Claude Code comparison: medium-high feasibility

Reasons:

- the same task set can be reused;
- hooks provide a stable capture point;
- normalized AgentRun traces make comparison possible.

Main risks:

- incomplete capture from hooks;
- safe automation of Claude Code over local fixtures;
- trace granularity mismatch.

Mitigations:

- capture tool calls/results first;
- use isolated temp directories for each case;
- compare at taxonomy and failure-pattern level rather than raw event parity.

### 7.3 SWE-bench path: medium feasibility, should be later

SWE-bench is valuable but should not be the first milestone. It requires Docker-based harness integration, many repository checkouts, heavier execution cost, and a dedicated adapter. It becomes appropriate after the local benchmark and Claude Code comparison paths prove the product loop.

## 8. Recommended Sequencing

1. Define local coding benchmark format and create 12 representative cases.
2. Run the cases with LumiAgent's own coding agent and capture AgentRun traces.
3. Verify pass/fail with test commands and store results as an Experiment.
4. Run Diagnosis Agent over failed traces and aggregate failure patterns.
5. Expose CLI/TUI review views for experiment, case, trace, evidence, suggestions, and rerun diff.
6. Apply prompt/config improvements manually and rerun the same benchmark.
7. Add Claude Code comparison path using the same task set and hooks-based capture.
8. Consider SWE-bench Lite only after the local and Claude Code loops work.

## 9. Implementation Decisions to Make Later

These choices should be resolved during implementation planning. They do not block this product-loop design:

1. Whether the local benchmark should live under `eval_sets/`, `tests/fixtures/`, or a new `benchmarks/` directory.
2. Whether the first runner should reuse the existing `EvaluationSuite` or introduce a separate benchmark experiment runner abstraction.
3. The minimal Experiment-level trace schema needed for aggregation and rerun comparison.
4. How much of the CLI/TUI review surface should be implemented before Diagnosis Agent is complete.
5. Which prompt/config fields are safe to mark as `auto_applicable` in the first MVP.
