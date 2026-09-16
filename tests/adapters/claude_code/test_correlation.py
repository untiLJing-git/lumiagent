from lumiagent.adapters.claude_code.correlation import correlate_events
from lumiagent.adapters.claude_code.hooks import build_hook_event


def event(i, phase, call="c", scope="main", tool="Bash"):
    payload = {
        "session_id": "s",
        "event_id": f"e{i}",
        "sequence": i,
        "tool_name": tool,
        "agent_id": scope,
        "phase": phase,
        "tool_use_id": call,
    }
    if phase == "tool_request":
        payload["tool_input"] = {"command": f"echo {call}"}
    else:
        payload["tool_response"] = {"stdout": call, "exit_code": 0}
    return build_hook_event(payload)


def test_interleaved_same_name_calls_use_id() -> None:
    rows = [
        event(1, "tool_request", "A"),
        event(2, "tool_request", "B"),
        event(3, "tool_result", "A"),
        event(4, "tool_result", "B"),
    ]
    before = [r.model_dump() for r in rows]
    result = correlate_events(rows)
    assert len(result.actions) == 2
    for action in result.actions:
        assert action.status == "paired"
        assert action.event.payload["tool_input"]["command"] == (
            "echo " + action.event.payload["tool_response"]["stdout"]
        )
    assert result.actions[0].source_event_ids == ["e1", "e3"]
    assert [r.model_dump() for r in rows] == before


def test_out_of_order_delivery_still_pairs() -> None:
    result = correlate_events([event(2, "tool_result"), event(1, "tool_request")])
    assert len(result.actions) == 1
    assert result.actions[0].status == "paired"


def test_missing_id_does_not_pair_by_tool_name() -> None:
    result = correlate_events([event(1, "tool_request", None), event(2, "tool_result", None)])
    assert len(result.actions) == 2
    assert all(a.status == "ambiguous" for a in result.actions)


def test_reused_call_id_and_scope() -> None:
    rows = [
        event(1, "tool_request", scope="one"),
        event(2, "tool_request", scope="two"),
        event(3, "tool_result", scope="two"),
        event(4, "tool_result", scope="one"),
    ]
    assert all(a.status == "paired" for a in correlate_events(rows).actions)
    rows.append(event(5, "tool_request", scope="one"))
    result = correlate_events(rows)
    assert sum(a.status == "ambiguous" for a in result.actions) == 3


def test_proven_duplicates_only() -> None:
    req = event(1, "tool_request")
    result = correlate_events([req, req.model_copy(), event(2, "tool_result")])
    assert result.duplicate_count == 1
    assert len(result.actions) == 1
    local = build_hook_event({"session_id": "s", "tool_name": "Read"})
    assert len(correlate_events([local, local.model_copy()]).actions) == 2


def test_conflicting_source_identity_is_not_deduplicated() -> None:
    req = event(1, "tool_request")
    conflict = req.model_copy(update={"payload": {"tool_input": {"command": "other"}}})
    result = correlate_events([req, conflict, event(2, "tool_result")])
    assert result.duplicate_count == 0
    assert all(a.status == "ambiguous" for a in result.actions)
    assert "source_identity_conflict" in result.issues


def test_missing_terminal_and_tool_mismatch() -> None:
    assert correlate_events([event(1, "tool_request")]).actions[0].status == "unpaired"
    rows = [event(1, "tool_request"), event(2, "tool_result", tool="Read")]
    assert all(a.status == "ambiguous" for a in correlate_events(rows).actions)


def test_permission_events_do_not_consume_request() -> None:
    rows = [event(1, "tool_request"), event(2, "permission_request"), event(3, "tool_result")]
    result = correlate_events(rows)
    assert sorted(a.status for a in result.actions) == ["not_applicable", "paired"]


def test_retry_with_new_call_id_preserves_both_attempts() -> None:
    rows = [
        event(1, "tool_request", "A"),
        event(2, "error", "A"),
        event(3, "tool_request", "B"),
        event(4, "tool_result", "B"),
    ]
    result = correlate_events(rows)
    assert len(result.actions) == 2
    assert result.actions[0].event.phase == "error"


def test_same_id_in_different_sessions_does_not_pair() -> None:
    req = event(1, "tool_request")
    res = event(2, "tool_result").model_copy(update={"session_id": "other"})
    assert all(a.status == "unpaired" for a in correlate_events([req, res]).actions)
