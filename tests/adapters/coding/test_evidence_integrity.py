from pathlib import Path

from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.hooks import build_hook_event
from lumiagent.adapters.coding.evidence import audit_coding_evidence, refresh_workflow_checks
from lumiagent.adapters.coding.viewer import render_coding_trace_summary
from lumiagent.tracing import validate_run
from lumiagent.tracing.serializer import from_json, to_json


def spans(roots):
    return [s for root in roots for s in [root, *spans(root.children)]]


def edit_run():
    return ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=[
            build_hook_event(
                {
                    "session_id": "s",
                    "sequence": 1,
                    "tool_name": "Edit",
                    "phase": "tool_result",
                    "status": "success",
                }
            )
        ],
    )


def checks(run):
    return next(
        a
        for s in spans(run.root_spans)
        for a in s.artifacts
        if a.metadata.get("type") == "coding_workflow_checks"
    )


def test_finding_references_final_run() -> None:
    run = edit_run()
    ids = {s.span_id for s in spans(run.root_spans)}
    artifact = checks(run)
    assert artifact.content["findings"]
    for finding in artifact.content["findings"]:
        assert set(finding["evidence_span_ids"]) <= ids
    validate_run(run)
    assert audit_coding_evidence(run).status == "valid"
    assert audit_coding_evidence(from_json(to_json(run))).status == "valid"


def test_old_dangling_reference_is_reported_without_mutation() -> None:
    run = edit_run()
    checks(run).content["findings"][0]["evidence_span_ids"] = ["not_here"]
    before = to_json(run)
    audit = audit_coding_evidence(run)
    assert audit.status == "invalid"
    assert any(i.code == "dangling_span" for i in audit.issues)
    text = "\n".join(render_coding_trace_summary(run, show_checks=True))
    assert "Evidence Quality" in text and "invalid" in text
    assert to_json(run) == before


def test_changed_subject_invalidates_cached_checks() -> None:
    run = edit_run()
    action = next(s for s in spans(run.root_spans) if s.kind.value == "tool")
    action.input = {"changed": True}
    assert any(i.code == "stale_subject" for i in audit_coding_evidence(run).issues)


def test_refresh_preserves_source_and_history() -> None:
    run = edit_run()
    artifact = checks(run)
    artifact.content["schema_version"] = "coding_workflow_checks.v1"
    artifact.content.pop("subject_digest", None)
    before = to_json(run)
    refreshed = refresh_workflow_checks(run)
    assert to_json(run) == before
    assert (
        len(
            [
                a
                for s in spans(refreshed.root_spans)
                for a in s.artifacts
                if a.metadata.get("type") == "coding_workflow_checks"
            ]
        )
        == 2
    )
    assert checks(refreshed).content == artifact.content
    assert any(
        a.metadata.get("supersedes_artifact_ids") == [artifact.artifact_id]
        for s in spans(refreshed.root_spans)
        for a in s.artifacts
    )


def test_group_creation_does_not_add_unused_spans() -> None:
    run = ClaudeCodeTraceConverter().convert(
        session_id="s",
        events=[
            build_hook_event(
                {
                    "session_id": "s",
                    "sequence": i,
                    "tool_name": "Read",
                    "phase": "tool_result",
                    "status": "success",
                }
            )
            for i in (1, 2, 3)
        ],
    )
    groups = [s for s in spans(run.root_spans) if s.metadata.get("type") == "context_gathering"]
    assert len(groups) == 1
    assert len(groups[0].children) == 3
    assert all(s.status.value != "running" for s in groups)


def test_legacy_real_fixture_is_read_only_and_not_trusted_as_current() -> None:
    path = Path("tests/adapters/claude_code/fixtures/real_session_sanitized_trace.json")
    raw = path.read_bytes()
    run = from_json(raw.decode("utf-8-sig"))
    text = "\n".join(render_coding_trace_summary(run, show_checks=True))
    assert "Evidence Quality" in text
    assert audit_coding_evidence(run).status != "valid"
    assert path.read_bytes() == raw


def test_changed_check_verdict_is_not_valid_current_evidence() -> None:
    run = edit_run()
    checks(run).content["status"] = "pass"
    assert audit_coding_evidence(run).status == "invalid"


def test_malformed_capabilities_and_limitations_do_not_crash_viewer() -> None:
    run = edit_run()
    run.metadata["capture_capabilities"] = {"gaps": 42}
    checks(run).content["limitations"] = 42
    lines = render_coding_trace_summary(run, show_checks=True)
    assert any("invalid" in line for line in lines)


def test_duplicate_artifact_identity_invalidates_audit() -> None:
    run = edit_run()
    artifact = checks(run)
    run.root_spans[0].artifacts.append(artifact.model_copy(deep=True))
    assert audit_coding_evidence(run).status == "invalid"


def test_invalid_core_structure_is_not_accepted_by_adapter_audit() -> None:
    run = edit_run()
    run.root_spans[0].run_id = "another_run"
    assert audit_coding_evidence(run).status == "invalid"
