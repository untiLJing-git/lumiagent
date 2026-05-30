"""Convert Claude Code events into Coding Agent AgentRun traces."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent
from lumiagent.adapters.coding.conventions import (
    CODING_ARTIFACT_ACTION_EVIDENCE,
    CODING_ARTIFACT_SEMANTIC_EVIDENCE,
    CODING_ARTIFACT_WORKFLOW_CHECKS,
    CODING_CONTEXT_GATHERING,
    CODING_DOMAIN,
    CODING_USER_PROMPT,
    CODING_VERIFICATION,
    CODING_WORKFLOW_CHECK,
    coding_metadata,
)
from lumiagent.adapters.coding.events import CodingSemanticEvidence
from lumiagent.adapters.coding.normalizer import normalize_hook_event
from lumiagent.adapters.coding.validator import validate_coding_workflow
from lumiagent.tracing import ArtifactKind, RunStatus, SpanKind, SpanStatus
from lumiagent.tracing.builder_writer import BuilderTraceWriter

if TYPE_CHECKING:
    from lumiagent.tracing.models import AgentRun


class ClaudeCodeTraceConverter:
    def convert(
        self,
        *,
        session_id: str,
        events: list[ClaudeCodeHookEvent],
        semantic_items: list[dict[str, Any]] | None = None,
    ) -> AgentRun:
        run = self._build_run(
            session_id=session_id,
            events=events,
            semantic_items=semantic_items or [],
            workflow_checks=None,
        )
        checks = validate_coding_workflow(run)
        return self._build_run(
            session_id=session_id,
            events=events,
            semantic_items=semantic_items or [],
            workflow_checks=checks.model_dump(mode="json"),
        )

    def _build_run(
        self,
        *,
        session_id: str,
        events: list[ClaudeCodeHookEvent],
        semantic_items: list[dict[str, Any]],
        workflow_checks: dict[str, Any] | None,
    ) -> AgentRun:
        writer = BuilderTraceWriter()
        writer.start_run(
            name=f"Claude Code session {session_id}",
            metadata={"domain": CODING_DOMAIN, "source": "claude_code"},
        )
        root_id = writer.start_span(
            "Coding Agent Run",
            kind=SpanKind.CUSTOM,
            metadata=coding_metadata("coding_agent_run", source="claude_code"),
        )
        parent_ids: dict[str, str] = {}
        parent_statuses: dict[str, list[SpanStatus]] = {}
        root_statuses: list[SpanStatus] = []
        self._write_semantic_items(writer, root_id, semantic_items or [])
        for event in _pair_tool_events(sorted(events, key=lambda item: item.sequence)):
            normalized = normalize_hook_event(event)
            parent_id = root_id
            if normalized.parent_convention == CODING_CONTEXT_GATHERING:
                parent_id = parent_ids.setdefault(
                    CODING_CONTEXT_GATHERING,
                    writer.start_span(
                        "Context Gathering",
                        parent_span_id=root_id,
                        metadata=coding_metadata(
                            CODING_CONTEXT_GATHERING,
                            source="claude_code_hook",
                        ),
                    ),
                )
            elif normalized.parent_convention == CODING_VERIFICATION:
                parent_id = parent_ids.setdefault(
                    CODING_VERIFICATION,
                    writer.start_span(
                        "Verification",
                        parent_span_id=root_id,
                        metadata=coding_metadata(
                            CODING_VERIFICATION,
                            source="claude_code_hook",
                        ),
                    ),
                )
            span_id = writer.start_span(
                normalized.name,
                kind=SpanKind.TOOL,
                parent_span_id=parent_id,
                input_value=(
                    normalized.action_evidence.arguments
                    if normalized.action_evidence is not None
                    else None
                ),
                metadata=coding_metadata(
                    normalized.convention,
                    source="claude_code_hook",
                    source_ids=normalized.source_event_ids,
                    evidence_types=["action_evidence"],
                    classification_reason=str(normalized.metadata.get("classification_reason", "")),
                ),
            )
            if normalized.action_evidence is not None:
                writer.add_artifact(
                    span_id,
                    name="Action Evidence",
                    kind=ArtifactKind.JSON,
                    content=normalized.action_evidence.model_dump(mode="json"),
                    metadata={"type": CODING_ARTIFACT_ACTION_EVIDENCE},
                )
            span_status = _span_status(normalized.status)
            writer.end_span(
                span_id,
                status=span_status,
                output=normalized.action_evidence.result if normalized.action_evidence else None,
            )
            if normalized.parent_convention in parent_ids:
                parent_statuses.setdefault(normalized.parent_convention, []).append(span_status)
            else:
                root_statuses.append(span_status)
        for parent_convention, parent_id in parent_ids.items():
            parent_status = _aggregate_span_status(parent_statuses.get(parent_convention, []))
            writer.end_span(parent_id, status=parent_status)
            root_statuses.append(parent_status)
        if workflow_checks is not None:
            check_id = writer.start_span(
                "Workflow Check",
                kind=SpanKind.CUSTOM,
                parent_span_id=root_id,
                metadata=coding_metadata(
                    CODING_WORKFLOW_CHECK,
                    source="workflow_validator",
                    evidence_types=["workflow_finding"],
                ),
            )
            writer.add_artifact(
                check_id,
                name="Workflow Checks",
                kind=ArtifactKind.JSON,
                content=workflow_checks,
                metadata={"type": CODING_ARTIFACT_WORKFLOW_CHECKS},
            )
            check_status = (
                SpanStatus.ERROR if workflow_checks["status"] == "error" else SpanStatus.SUCCESS
            )
            writer.end_span(check_id, status=check_status)
            root_statuses.append(check_status)
        root_status = _aggregate_span_status(root_statuses)
        writer.end_span(root_id, status=root_status)
        return writer.flush(status=_run_status(root_status))

    def _write_semantic_items(
        self,
        writer: BuilderTraceWriter,
        root_id: str,
        semantic_items: list[dict[str, Any]],
    ) -> None:
        for item in semantic_items:
            evidence_input = {
                key: value for key, value in item.items() if key not in {"item_id", "timestamp"}
            }
            evidence = CodingSemanticEvidence.model_validate(evidence_input)
            span_id = writer.start_span(
                _semantic_name(evidence.convention),
                kind=SpanKind.CUSTOM,
                parent_span_id=root_id,
                metadata=coding_metadata(
                    evidence.convention,
                    source="transcript_enrichment",
                    evidence_types=["semantic_evidence"],
                    extra={
                        "source_item_ids": [str(item.get("item_id", ""))],
                        "confidence": evidence.confidence,
                    },
                ),
            )
            writer.add_artifact(
                span_id,
                name="Semantic Evidence",
                kind=ArtifactKind.JSON,
                content=evidence.model_dump(mode="json"),
                metadata={"type": CODING_ARTIFACT_SEMANTIC_EVIDENCE},
            )
            writer.end_span(span_id, status=SpanStatus.SUCCESS)


def _pair_tool_events(events: list[ClaudeCodeHookEvent]) -> list[ClaudeCodeHookEvent]:
    paired: list[ClaudeCodeHookEvent] = []
    pending: ClaudeCodeHookEvent | None = None
    for event in events:
        if event.phase == "tool_request":
            if pending is not None:
                paired.append(pending)
            pending = event
            continue
        if event.phase == "permission_request":
            paired.append(event)
            continue
        if pending is not None and _can_pair(pending, event):
            paired.append(_merge_tool_events(pending, event))
            pending = None
            continue
        if pending is not None:
            paired.append(pending)
            pending = None
        paired.append(event)
    if pending is not None:
        paired.append(pending)
    return paired


def _can_pair(request: ClaudeCodeHookEvent, result: ClaudeCodeHookEvent) -> bool:
    return result.phase in {"tool_result", "error"} and request.tool_name == result.tool_name


def _merge_tool_events(
    request: ClaudeCodeHookEvent,
    result: ClaudeCodeHookEvent,
) -> ClaudeCodeHookEvent:
    payload = {**request.payload, **result.payload}
    payload["_source_event_ids"] = [request.event_id, result.event_id]
    if "tool_input" not in payload and "tool_input" in request.payload:
        payload["tool_input"] = request.payload["tool_input"]
    safety = result.safety if result.safety != {"redaction_state": "raw"} else request.safety
    return ClaudeCodeHookEvent(
        event_id=result.event_id,
        session_id=result.session_id,
        sequence=result.sequence,
        timestamp=result.timestamp or request.timestamp,
        source=result.source,
        hook_name=result.hook_name,
        tool_name=result.tool_name,
        phase=result.phase,
        working_directory=result.working_directory or request.working_directory,
        payload=payload,
        safety=safety,
    )
def _span_status(status: str) -> SpanStatus:
    if status == "error":
        return SpanStatus.ERROR
    if status == "running":
        return SpanStatus.RUNNING
    if status == "unknown":
        return SpanStatus.SKIPPED
    return SpanStatus.SUCCESS


def _aggregate_span_status(statuses: list[SpanStatus]) -> SpanStatus:
    if any(status == SpanStatus.ERROR for status in statuses):
        return SpanStatus.ERROR
    if any(status == SpanStatus.RUNNING for status in statuses):
        return SpanStatus.RUNNING
    return SpanStatus.SUCCESS


def _run_status(root_status: SpanStatus) -> RunStatus:
    if root_status == SpanStatus.ERROR:
        return RunStatus.ERROR
    if root_status == SpanStatus.RUNNING:
        return RunStatus.RUNNING
    return RunStatus.SUCCESS


def _semantic_name(convention: str) -> str:
    if convention == CODING_USER_PROMPT:
        return "User Prompt"
    return convention.replace("_", " ").title()
