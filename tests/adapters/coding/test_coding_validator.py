from lumiagent.adapters.coding.validator import validate_coding_workflow
from lumiagent.tracing import AgentRun, RunStatus, SpanKind, SpanStatus, TraceBuilder


def _run_with_spans(span_types: list[tuple[str, SpanStatus]]) -> AgentRun:
    builder = TraceBuilder(name="coding run")
    root_id = builder.start_span(
        "Coding Agent Run",
        metadata={"domain": "coding_agent", "type": "coding_agent_run"},
    )
    for span_type, status in span_types:
        span_id = builder.start_span(
            span_type.replace("_", " ").title(),
            kind=SpanKind.TOOL,
            parent_span_id=root_id,
            metadata={"domain": "coding_agent", "type": span_type},
        )
        builder.end_span(span_id, status=status)
    builder.end_span(root_id, status=SpanStatus.SUCCESS)
    return builder.build(status=RunStatus.SUCCESS)


def test_code_edit_without_verification_warns() -> None:
    checks = validate_coding_workflow(_run_with_spans([("code_edit", SpanStatus.SUCCESS)]))

    assert checks.status == "warning"
    assert checks.findings[0].rule_id == "code_edit_requires_verification"
    assert checks.findings[0].severity == "warning"


def test_code_edit_with_test_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([("code_edit", SpanStatus.SUCCESS), ("test_run", SpanStatus.SUCCESS)])
    )

    assert checks.status == "pass"
    assert checks.findings == []


def test_failed_test_without_recovery_errors() -> None:
    checks = validate_coding_workflow(_run_with_spans([("test_run", SpanStatus.ERROR)]))

    assert checks.status == "error"
    assert checks.findings[0].rule_id == "failed_test_requires_recovery"


def test_failed_command_without_recovery_warns() -> None:
    checks = validate_coding_workflow(_run_with_spans([("shell_command", SpanStatus.ERROR)]))

    assert checks.status == "warning"
    assert checks.findings[0].rule_id == "failed_command_requires_recovery"


def test_failed_command_with_recovery_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([
            ("shell_command", SpanStatus.ERROR),
            ("failure_recovery", SpanStatus.SUCCESS),
        ])
    )

    assert checks.status == "pass"


def test_permission_denied_followed_by_risky_action_errors() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([
            ("approval_decision", SpanStatus.ERROR),
            ("shell_command", SpanStatus.SUCCESS),
        ])
    )

    assert checks.status == "error"
    assert checks.findings[0].rule_id == "permission_denied_blocks_action"


def test_final_response_after_unresolved_error_warns() -> None:
    checks = validate_coding_workflow(
        _run_with_spans([
            ("error_observed", SpanStatus.ERROR),
            ("final_response", SpanStatus.SUCCESS),
        ])
    )

    assert checks.status == "warning"
    assert checks.findings[0].rule_id == "final_response_after_unresolved_error"


def test_failed_test_with_recovery_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans(
            [
                ("test_run", SpanStatus.ERROR),
                ("failure_recovery", SpanStatus.SUCCESS),
            ]
        )
    )

    assert checks.status == "pass"


def test_permission_denied_followed_by_non_risky_action_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans(
            [
                ("approval_decision", SpanStatus.ERROR),
                ("final_response", SpanStatus.SUCCESS),
            ]
        )
    )

    assert checks.status == "pass"


def test_final_response_after_recovered_error_passes() -> None:
    checks = validate_coding_workflow(
        _run_with_spans(
            [
                ("error_observed", SpanStatus.ERROR),
                ("failure_recovery", SpanStatus.SUCCESS),
                ("final_response", SpanStatus.SUCCESS),
            ]
        )
    )

    assert checks.status == "pass"


def test_nested_spans_are_flattened_in_workflow_order() -> None:
    builder = TraceBuilder(name="coding run")
    root_id = builder.start_span(
        "Coding Agent Run",
        metadata={"domain": "coding_agent", "type": "coding_agent_run"},
    )
    edit_group_id = builder.start_span(
        "Edit Group",
        kind=SpanKind.CUSTOM,
        parent_span_id=root_id,
        metadata={"domain": "coding_agent", "type": "context_gathering"},
    )
    edit_id = builder.start_span(
        "Code Edit",
        kind=SpanKind.TOOL,
        parent_span_id=edit_group_id,
        metadata={"domain": "coding_agent", "type": "code_edit"},
    )
    builder.end_span(edit_id, status=SpanStatus.SUCCESS)
    builder.end_span(edit_group_id, status=SpanStatus.SUCCESS)
    test_id = builder.start_span(
        "Test Run",
        kind=SpanKind.TOOL,
        parent_span_id=root_id,
        metadata={"domain": "coding_agent", "type": "test_run"},
    )
    builder.end_span(test_id, status=SpanStatus.SUCCESS)
    builder.end_span(root_id, status=SpanStatus.SUCCESS)

    checks = validate_coding_workflow(builder.build(status=RunStatus.SUCCESS))

    assert checks.status == "pass"
