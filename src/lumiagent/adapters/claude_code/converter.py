"""Convert hooks into a single immutable-identity action graph and audited prechecks."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from lumiagent.adapters.claude_code.correlation import (
    CorrelatedAction,
    CorrelationResult,
    call_key,
    correlate_events,
)
from lumiagent.adapters.coding.conventions import coding_metadata
from lumiagent.adapters.coding.events import (
    Availability,
    CaptureCapabilities,
    CodingSemanticEvidence,
)
from lumiagent.adapters.coding.evidence import append_workflow_checks
from lumiagent.adapters.coding.normalizer import normalize_hook_event
from lumiagent.adapters.coding.ordering import SourcePosition, parse_source_time
from lumiagent.tracing import AgentRun, ArtifactKind, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder_writer import BuilderTraceWriter

if TYPE_CHECKING:
    from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent


def _position(action: CorrelatedAction) -> SourcePosition:
    request, result = action.request, action.result
    # A terminal-only record locates an observation, not an inferred full action interval.
    start = request or result or action.event
    end = result or (action.event if request is None else None)
    key = call_key(action.event)
    return SourcePosition(
        session_id=action.event.session_id,
        scope_id=key[2] if key else action.event.scope_id,
        sequence_start=start.source_sequence,
        sequence_end=end.source_sequence if end else None,
        started_at=start.timestamp,
        ended_at=end.timestamp if end else None,
    )


def _availability(flags: list[bool]) -> Availability:
    if not flags or not any(flags):
        return "unavailable"
    return "available" if all(flags) else "partial"


def _valid_source_times(position: SourcePosition) -> bool:
    start = parse_source_time(position.started_at)
    end = parse_source_time(position.ended_at)
    return start is not None and end is not None and start <= end


def _capabilities(
    result: CorrelationResult, coverage: CaptureCapabilities | None
) -> CaptureCapabilities:
    caps = CaptureCapabilities(
        workflow_coverage=coverage.workflow_coverage if coverage else "unknown",
        coverage_basis=coverage.coverage_basis if coverage else None,
        gaps=list(coverage.gaps) if coverage else [],
    )
    actions = [a for a in result.actions if a.status != "not_applicable"]
    caps.source_identity = _availability([a.event.source_event_id is not None for a in actions])
    caps.call_identity = _availability([a.status == "paired" for a in actions])
    positions = [_position(a) for a in actions]
    caps.source_order = _availability(
        [
            p.sequence_start is not None
            and p.sequence_end is not None
            and p.sequence_end >= p.sequence_start
            for p in positions
        ]
    )
    caps.source_time = _availability(
        [
            _valid_source_times(p) and a.status == "paired"
            for p, a in zip(positions, actions, strict=True)
        ]
    )
    payload_flags: list[bool] = []
    for action in actions:
        request_payload = action.request.payload if action.request else {}
        result_payload = action.result.payload if action.result else {}
        payload_flags.extend(
            [
                any(
                    isinstance(request_payload.get(key), dict)
                    for key in ("tool_input", "arguments")
                ),
                any(key in result_payload for key in ("tool_response", "result")),
            ]
        )
    caps.action_payloads = _availability(payload_flags)
    for action in actions:
        payload = action.event.payload
        raw = payload.get("tool_response", payload.get("result"))
        if payload.get("output_truncated") is True or (
            isinstance(raw, dict) and raw.get("output_truncated") is True
        ):
            caps.gaps.append("tool_result_truncated")
            caps.action_payloads = "partial"
        if "[REDACTED]" in json.dumps(payload):
            caps.gaps.append("possible_redaction_loss")
            caps.action_payloads = "partial"
    caps.gaps.extend(result.issues)
    if result.issues:
        caps.workflow_coverage = "partial"
    if caps.workflow_coverage != "complete":
        caps.gaps.append("workflow_completeness_not_established")
    if caps.source_order != "available":
        caps.gaps.append("source_order_missing_or_partial")
    if caps.source_time != "available":
        caps.gaps.append("source_duration_unavailable_for_some_actions")
    caps.gaps = sorted(set(caps.gaps))
    return caps


class ClaudeCodeTraceConverter:
    def convert(
        self,
        *,
        session_id: str,
        events: list[ClaudeCodeHookEvent],
        semantic_items: list[dict[str, Any]] | None = None,
        coverage: CaptureCapabilities | None = None,
    ) -> AgentRun:
        if any(event.session_id != session_id for event in events):
            raise ValueError("Cannot merge events from different sessions")
        correlated = correlate_events(events)
        caps = _capabilities(correlated, coverage)
        semantic_items = semantic_items or []
        caps.task_input = (
            "available"
            if any(item.get("convention") == "user_prompt" for item in semantic_items)
            else "unavailable"
        )
        caps.final_response = (
            "available"
            if any(item.get("convention") == "final_response" for item in semantic_items)
            else "unavailable"
        )
        writer = BuilderTraceWriter()
        writer.start_run(
            name=f"Claude Code session {session_id}",
            metadata={
                "domain": "coding_agent",
                "source": "claude_code",
                "timestamp_basis": "ingestion",
                "capture_capabilities": caps.model_dump(mode="json"),
                "correlation": {
                    "issues": correlated.issues,
                    "duplicate_count": correlated.duplicate_count,
                },
            },
        )
        root_id = writer.start_span(
            "Coding Agent Run",
            metadata=coding_metadata(
                "coding_agent_run", source="claude_code", extra={"timestamp_basis": "ingestion"}
            ),
        )
        parents: dict[str, str] = {}
        statuses: dict[str, list[SpanStatus]] = {}
        root_statuses: list[SpanStatus] = []
        for action in correlated.actions:
            event = action.event
            normalized = normalize_hook_event(event)
            parent_id = root_id
            group = normalized.parent_convention
            if group is not None:
                if group not in parents:
                    parents[group] = writer.start_span(
                        group.replace("_", " ").title(),
                        parent_span_id=root_id,
                        metadata=coding_metadata(
                            group,
                            source="claude_code_hook",
                            extra={"timestamp_basis": "ingestion", "semantic_group": True},
                        ),
                    )
                    statuses[group] = []
                parent_id = parents[group]
            position = _position(action)
            key = call_key(event)
            extra: dict[str, Any] = {
                "source_order": position.model_dump(mode="json"),
                "timestamp_basis": "ingestion",
                "correlation_status": action.status,
                "capture_ids": action.capture_ids,
                "observation_only": action.status != "paired",
                "ingestion_index": action.input_index,
                "call_id": key[3] if key else None,
                "working_directory": event.working_directory,
            }
            span_id = writer.start_span(
                normalized.name,
                kind=SpanKind.TOOL,
                parent_span_id=parent_id,
                input_value=normalized.action_evidence.arguments
                if normalized.action_evidence
                else None,
                metadata=coding_metadata(
                    normalized.convention,
                    source="claude_code_hook",
                    source_ids=action.source_event_ids,
                    evidence_types=["action_evidence"],
                    classification_reason=str(normalized.metadata.get("classification_reason", "")),
                    extra=extra,
                ),
            )
            evidence = normalized.action_evidence
            if evidence is not None:
                writer.add_artifact(
                    span_id,
                    name="Action Evidence",
                    kind=ArtifactKind.JSON,
                    content=evidence.model_dump(mode="json"),
                    metadata={"type": "coding_action_evidence"},
                )
            status = {
                "success": SpanStatus.SUCCESS,
                "error": SpanStatus.ERROR,
                "running": SpanStatus.RUNNING,
            }.get(normalized.status, SpanStatus.SKIPPED)
            writer.end_span(span_id, status=status, output=evidence.result if evidence else None)
            if group is not None:
                statuses[group].append(status)
            else:
                root_statuses.append(status)
        for group, parent_id in parents.items():
            status = _aggregate(statuses[group])
            writer.end_span(parent_id, status=status)
            root_statuses.append(status)
        # Semantics retain source positions. Appending is storage order, not a temporal claim.
        for item in semantic_items:
            semantic = CodingSemanticEvidence.model_validate(
                {key: value for key, value in item.items() if key not in {"item_id", "timestamp"}}
            )
            position = SourcePosition(
                session_id=session_id,
                scope_id="transcript",
                started_at=item.get("timestamp"),
                ended_at=item.get("timestamp"),
            )
            span_id = writer.start_span(
                semantic.convention.replace("_", " ").title(),
                parent_span_id=root_id,
                metadata=coding_metadata(
                    semantic.convention,
                    source="transcript_enrichment",
                    evidence_types=["semantic_evidence"],
                    extra={
                        "source_item_ids": [str(item.get("item_id", ""))],
                        "confidence": semantic.confidence,
                        "source_order": position.model_dump(mode="json"),
                        "timestamp_basis": "ingestion",
                        "observation_only": True,
                    },
                ),
            )
            writer.add_artifact(
                span_id,
                name="Semantic Evidence",
                kind=ArtifactKind.JSON,
                content=semantic.model_dump(mode="json"),
                metadata={"type": "coding_semantic_evidence"},
            )
            writer.end_span(span_id, status=SpanStatus.SUCCESS)
        status = _aggregate(root_statuses)
        writer.end_span(root_id, status=status)
        run_status = {
            SpanStatus.ERROR: RunStatus.ERROR,
            SpanStatus.RUNNING: RunStatus.RUNNING,
            SpanStatus.SUCCESS: RunStatus.SUCCESS,
        }.get(status, RunStatus.PENDING)
        run = writer.flush(status=run_status)
        append_workflow_checks(run)
        return run


def _aggregate(statuses: list[SpanStatus]) -> SpanStatus:
    if SpanStatus.ERROR in statuses:
        return SpanStatus.ERROR
    if SpanStatus.RUNNING in statuses:
        return SpanStatus.RUNNING
    if not statuses or SpanStatus.SKIPPED in statuses:
        return SpanStatus.SKIPPED
    return SpanStatus.SUCCESS
