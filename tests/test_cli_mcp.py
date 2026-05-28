from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from lumiagent.cli import app
from lumiagent.tracing import AgentRun, RunStatus
from lumiagent.tracing.serializer import to_json

runner = CliRunner()


def utc_now() -> datetime:
    return datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC)


def make_run(name: str = "cli trace") -> AgentRun:
    return AgentRun(
        run_id="run_cli",
        name=name,
        status=RunStatus.SUCCESS,
        started_at=utc_now(),
        ended_at=utc_now(),
        root_spans=[],
    )


def test_capture_mcp_rejects_invalid_arguments_json() -> None:
    result = runner.invoke(
        app,
        [
            "capture",
            "mcp",
            "--server-command",
            "example-server",
            "--tool",
            "example-tool",
            "--arguments",
            "not-json",
            "--output",
            "trace.json",
        ],
    )

    assert result.exit_code != 0
    assert "arguments must be a JSON object" in result.output


def test_capture_mcp_rejects_valid_non_object_arguments_json() -> None:
    result = runner.invoke(
        app,
        [
            "capture",
            "mcp",
            "--server-command",
            "example-server",
            "--tool",
            "example-tool",
            "--arguments",
            "[]",
            "--output",
            "trace.json",
        ],
    )

    assert result.exit_code != 0
    assert "arguments must be a JSON object" in result.output


def test_capture_mcp_accepts_timeout_alias(monkeypatch: Any, tmp_path: Path) -> None:
    captured_configs: list[Any] = []

    class FakeMcpCaptureStrategy:
        def __init__(self, *, config: Any) -> None:
            captured_configs.append(config)

        def capture(self) -> AgentRun:
            return make_run("captured cli trace")

    monkeypatch.setattr(
        "lumiagent.adapters.mcp.capture.McpCaptureStrategy", FakeMcpCaptureStrategy
    )
    trace_path = tmp_path / "trace.json"

    result = runner.invoke(
        app,
        [
            "capture",
            "mcp",
            "--server-command",
            "example-server",
            "--tool",
            "example-tool",
            "--timeout",
            "7",
            "--output",
            str(trace_path),
        ],
    )

    assert result.exit_code == 0
    assert captured_configs[0].timeout_seconds == 7
    assert trace_path.exists()


def test_capture_mcp_runtime_not_implemented_does_not_create_output(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "nested" / "trace.json"

    result = runner.invoke(
        app,
        [
            "capture",
            "mcp",
            "--server-command",
            "example-server",
            "--tool",
            "example-tool",
            "--output",
            str(trace_path),
        ],
    )

    assert result.exit_code != 0
    assert "MCP stdio capture is not implemented yet" in result.output
    assert not trace_path.exists()


def test_show_reports_malformed_trace_file(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("not-json", encoding="utf-8")

    result = runner.invoke(app, ["show", str(trace_path)])

    assert result.exit_code != 0
    assert "Invalid trace JSON" in result.output


def test_show_renders_minimal_trace_file(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(to_json(make_run()), encoding="utf-8")

    result = runner.invoke(app, ["show", str(trace_path)])

    assert result.exit_code == 0
    assert "Run: cli trace" in result.output


def test_capture_mcp_accepts_repeated_server_args(
    monkeypatch: Any, tmp_path: Path
) -> None:
    captured_configs: list[Any] = []

    class FakeMcpCaptureStrategy:
        def __init__(self, *, config: Any) -> None:
            captured_configs.append(config)

        def capture(self) -> AgentRun:
            return make_run("captured cli trace")

    monkeypatch.setattr(
        "lumiagent.adapters.mcp.capture.McpCaptureStrategy", FakeMcpCaptureStrategy
    )
    trace_path = tmp_path / "nested" / "trace.json"

    result = runner.invoke(
        app,
        [
            "capture",
            "mcp",
            "--server-command",
            "example-server",
            "--server-arg",
            "--flag",
            "--server-arg",
            "value",
            "--tool",
            "example-tool",
            "--arguments",
            '{"x": 1}',
            "--output",
            str(trace_path),
        ],
    )

    assert result.exit_code == 0
    assert captured_configs[0].server_args == ["--flag", "value"]
    assert captured_configs[0].arguments == {"x": 1}
    assert trace_path.exists()
