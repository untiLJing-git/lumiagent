"""Plain-text Coding Agent trace summary viewer."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_DOMAIN,
)

if TYPE_CHECKING:
    from lumiagent.tracing import AgentRun, Artifact, Span


def is_coding_trace(run: AgentRun) -> bool:
    if run.metadata.get("domain") == CODING_DOMAIN:
        return True
    return any(span.metadata.get("domain") == CODING_DOMAIN for span in run.root_spans)


def render_coding_trace_summary(
    run: AgentRun,
    *,
    show_checks: bool = False,
) -> list[str]:
    lines = [f"Run: {run.name}", f"Status: {run.status.value}"]
    lines.append("Semantic Summary")
    semantic_artifacts = _artifacts_by_type(
        run.root_spans,
        CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    )
    if semantic_artifacts:
        for artifact in semantic_artifacts:
            content = _artifact_content(artifact)
            summary = content.get("content_summary") or artifact.name
            convention = content.get("convention")
            prefix = f"  - {convention}: " if convention else "  - "
            lines.append(f"{prefix}{_display(summary)}")
    else:
        lines.append("  (none)")

    lines.append("Span Tree")
    for span in run.root_spans:
        _render_span(lines, span, depth=0)

    lines.append("Workflow Checks")
    check_artifacts = _artifacts_by_type(run.root_spans, CODING_ARTIFACT_WORKFLOW_CHECKS)
    if check_artifacts:
        for artifact in check_artifacts:
            _render_workflow_checks(lines, artifact, show_checks=show_checks)
    else:
        lines.append("  (none)")

    return lines


def _render_span(lines: list[str], span: Span, *, depth: int) -> None:
    indent = "  " * depth
    span_type = span.metadata.get("type")
    suffix = f" type={span_type}" if span_type else ""
    lines.append(f"{indent}- {span.name} [{span.status.value}]{suffix}")
    for child in span.children:
        _render_span(lines, child, depth=depth + 1)


def _render_workflow_checks(
    lines: list[str],
    artifact: Artifact,
    *,
    show_checks: bool,
) -> None:
    content = _artifact_content(artifact)
    lines.append(f"  status: {_display(content.get('status'))}")
    findings = content.get("findings")
    if not isinstance(findings, list) or not findings:
        lines.append("  findings: none")
        return
    if not show_checks:
        lines.append(f"  findings: {len(findings)}")
        return
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        evidence = finding.get("evidence_span_ids")
        if isinstance(evidence, list):
            evidence_text = ", ".join(str(item) for item in evidence)
        else:
            evidence_text = ""
        lines.append(
            "  - "
            f"rule_id={_display(finding.get('rule_id'))} "
            f"severity={_display(finding.get('severity'))} "
            f"evidence_span_ids={evidence_text}"
        )


def _artifacts_by_type(spans: list[Span], artifact_type: str) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for span in spans:
        artifacts.extend(
            artifact
            for artifact in span.artifacts
            if artifact.metadata.get("type") == artifact_type
        )
        artifacts.extend(_artifacts_by_type(span.children, artifact_type))
    return artifacts


def _artifact_content(artifact: Artifact) -> dict[str, Any]:
    if isinstance(artifact.content, dict):
        return artifact.content
    return {}


def _display(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)
