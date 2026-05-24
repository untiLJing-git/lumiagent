"""Structural validation for Agent traces."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .enums import TargetType

if TYPE_CHECKING:
    from .models import AgentRun, Span


class TraceValidationError(ValueError):
    pass


def _flatten_spans(spans: list[Span]) -> list[Span]:
    flattened: list[Span] = []
    for span in spans:
        flattened.append(span)
        flattened.extend(_flatten_spans(span.children))
    return flattened


def _validate_child_parent_links(span: Span) -> None:
    for child in span.children:
        if child.parent_span_id != span.span_id:
            raise TraceValidationError(
                f"Span {child.span_id} parent mismatch: "
                f"expected {span.span_id}, got {child.parent_span_id}"
            )
        _validate_child_parent_links(child)


def _validate_target(
    target_type: TargetType,
    target_id: str,
    run: AgentRun,
    span_ids: set[str],
) -> None:
    if target_type is TargetType.RUN:
        if target_id != run.run_id:
            raise TraceValidationError(
                f"target_id {target_id} does not match run_id {run.run_id}"
            )
        return
    if target_id not in span_ids:
        raise TraceValidationError(f"target_id {target_id} does not reference an existing span")


def _validate_evidence(evidence_span_ids: list[str], span_ids: set[str]) -> None:
    for span_id in evidence_span_ids:
        if span_id not in span_ids:
            raise TraceValidationError(f"evidence span {span_id} does not exist")


def validate_run(run: AgentRun) -> None:
    spans = _flatten_spans(run.root_spans)
    span_ids: set[str] = set()

    for root in run.root_spans:
        if root.parent_span_id is not None:
            raise TraceValidationError(f"Root span {root.span_id} must not have parent_span_id")

    for span in spans:
        if span.run_id != run.run_id:
            raise TraceValidationError(
                f"Span {span.span_id} run_id does not match AgentRun {run.run_id}"
            )
        if span.span_id in span_ids:
            raise TraceValidationError(f"Duplicate span_id {span.span_id}")
        span_ids.add(span.span_id)

    for root in run.root_spans:
        _validate_child_parent_links(root)

    for span in spans:
        if span.parent_span_id is not None and span.parent_span_id not in span_ids:
            raise TraceValidationError(
                f"Span {span.span_id} parent_span_id {span.parent_span_id} does not exist"
            )

    for evaluation in run.evaluations:
        _validate_target(evaluation.target_type, evaluation.target_id, run, span_ids)
        _validate_evidence(evaluation.evidence_span_ids, span_ids)

    for diagnosis in run.diagnoses:
        _validate_target(diagnosis.target_type, diagnosis.target_id, run, span_ids)
        _validate_evidence(diagnosis.evidence_span_ids, span_ids)
