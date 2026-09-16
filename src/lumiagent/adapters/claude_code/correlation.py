"""Conservative, non-mutating correlation of external tool lifecycle events."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lumiagent.adapters.claude_code.events import ClaudeCodeHookEvent  # noqa: TC001

CorrelationStatus = Literal["paired", "unpaired", "ambiguous", "not_applicable"]


class CorrelatedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: ClaudeCodeHookEvent
    request: ClaudeCodeHookEvent | None = None
    result: ClaudeCodeHookEvent | None = None
    status: CorrelationStatus
    source_event_ids: list[str]
    capture_ids: list[str]
    input_index: int


class CorrelationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: list[CorrelatedAction] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    duplicate_count: int = 0


def _identity(event: ClaudeCodeHookEvent) -> tuple[str, str, str, str] | None:
    # A v1 event_id may have been generated as evt_1; never assume it is authoritative.
    value = event.source_event_id or event.payload.get("event_id")
    if not isinstance(value, str) or not value:
        return None
    return event.source, event.session_id, event.scope_id, value


def call_key(event: ClaudeCodeHookEvent) -> tuple[str, str, str, str] | None:
    value = event.call_id or event.payload.get("tool_use_id") or event.payload.get("call_id")
    scope = event.payload.get("agent_id") or event.payload.get("subagent_id") or event.scope_id
    if not isinstance(value, str) or not value:
        return None
    return event.source, event.session_id, str(scope), value


def _content(event: ClaudeCodeHookEvent) -> str:
    value = event.model_dump(exclude={"capture_id", "observed_at", "ingestion_index"})
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _single(index: int, event: ClaudeCodeHookEvent, status: CorrelationStatus) -> CorrelatedAction:
    return CorrelatedAction(
        event=event.model_copy(deep=True),
        request=event if event.phase == "tool_request" else None,
        result=event if event.phase in {"tool_result", "error"} else None,
        status=status,
        source_event_ids=[event.event_id],
        capture_ids=[event.capture_id or f"input_{index}"],
        input_index=index,
    )


def correlate_events(events: list[ClaudeCodeHookEvent]) -> CorrelationResult:
    output = CorrelationResult()
    identities: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for event in events:
        identity = _identity(event)
        if identity is not None:
            identities[identity].add(_content(event))
    conflicts = {key for key, values in identities.items() if len(values) > 1}
    if conflicts:
        output.issues.append("source_identity_conflict")
    seen: set[tuple[str, str, str, str]] = set()
    groups: dict[tuple[str, str, str, str], list[tuple[int, ClaudeCodeHookEvent]]] = defaultdict(
        list
    )
    for index, event in enumerate(events):
        identity = _identity(event)
        if identity is not None and identity not in conflicts:
            if identity in seen:
                output.duplicate_count += 1
                continue
            seen.add(identity)
        if event.phase == "permission_request":
            output.actions.append(_single(index, event, "not_applicable"))
        elif (key := call_key(event)) is None:
            output.actions.append(_single(index, event, "ambiguous"))
            output.issues.append("missing_call_id")
        else:
            groups[key].append((index, event))

    for rows in groups.values():
        requests = [(i, e) for i, e in rows if e.phase == "tool_request"]
        results = [(i, e) for i, e in rows if e.phase in {"tool_result", "error"}]
        conflict = any(_identity(e) in conflicts for _, e in rows)
        pairable = len(requests) == len(results) == 1 and not conflict
        if pairable:
            req_index, request = requests[0]
            res_index, result = results[0]
            pairable = request.tool_name is not None and request.tool_name == result.tool_name
        if not pairable:
            status: CorrelationStatus = (
                "unpaired" if len(rows) == 1 and not conflict else "ambiguous"
            )
            output.actions.extend(_single(i, e, status) for i, e in rows)
            output.issues.append(f"{status}_call")
            continue
        req_index, request = requests[0]
        res_index, result = results[0]
        payload = {**request.payload, **result.payload}
        # Inputs belong to the request, not to a terminal event that can contain other data.
        for name in ("tool_input", "arguments"):
            if name in request.payload:
                payload[name] = request.payload[name]
        output.actions.append(
            CorrelatedAction(
                event=result.model_copy(
                    update={
                        "payload": payload,
                        "working_directory": result.working_directory or request.working_directory,
                    },
                    deep=True,
                ),
                request=request,
                result=result,
                status="paired",
                source_event_ids=[request.event_id, result.event_id],
                capture_ids=[
                    request.capture_id or f"input_{req_index}",
                    result.capture_id or f"input_{res_index}",
                ],
                input_index=min(req_index, res_index),
            )
        )
    output.actions.sort(key=lambda action: action.input_index)
    output.issues = sorted(set(output.issues))
    return output
