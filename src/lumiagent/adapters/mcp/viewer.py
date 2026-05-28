"""Plain-text MCP trace summary viewer."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lumiagent.adapters.mcp.conventions import MCP_ARTIFACT_TOOL_SELECTION

if TYPE_CHECKING:
    from lumiagent.tracing import AgentRun, Artifact, Diagnosis, Span


def render_mcp_trace_summary(run: AgentRun) -> list[str]:
    """Render a plain string summary for an MCP trace run."""

    lines = [f"Run: {run.name}", f"Status: {run.status.value}"]
    for span in run.root_spans:
        _render_span(lines, span, depth=0)

    selection = _first_tool_selection_artifact(run.root_spans)
    if selection is not None:
        content = _artifact_content(selection)
        lines.extend(
            [
                "Tool Selection",
                f"  requested: {_display(content.get('requested_tool_name'))}",
                f"  selected: {_display(content.get('selected_tool_name'))}",
            ]
        )

    if run.diagnoses:
        _render_failure(lines, run.diagnoses[0], selection)

    return lines


def _render_span(lines: list[str], span: Span, *, depth: int) -> None:
    indent = "  " * depth
    lines.append(f"{indent}- {span.name} [{span.status.value}]")
    for child in span.children:
        _render_span(lines, child, depth=depth + 1)


def _first_tool_selection_artifact(spans: list[Span]) -> Artifact | None:
    for span in spans:
        for artifact in span.artifacts:
            if artifact.metadata.get("type") == MCP_ARTIFACT_TOOL_SELECTION:
                return artifact
        found = _first_tool_selection_artifact(span.children)
        if found is not None:
            return found
    return None


def _render_failure(
    lines: list[str], diagnosis: Diagnosis, selection: Artifact | None
) -> None:
    lines.extend(["MCP Failure", f"  type: {diagnosis.failure_type}"])
    if selection is not None:
        content = _artifact_content(selection)
        lines.append(f"  requested tool: {_display(content.get('requested_tool_name'))}")
    if diagnosis.evidence_span_ids:
        lines.append(f"  evidence spans: {', '.join(diagnosis.evidence_span_ids)}")


def _artifact_content(artifact: Artifact) -> dict[str, Any]:
    if isinstance(artifact.content, dict):
        return artifact.content
    return {}


def _display(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)
