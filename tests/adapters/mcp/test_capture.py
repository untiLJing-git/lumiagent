from typing import Any

import pytest
from pydantic import ValidationError

from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
from lumiagent.adapters.mcp.runtime import (
    McpConnectionInfo,
    McpRuntimeError,
    McpRuntimeStage,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType
from lumiagent.tracing import RunStatus
from lumiagent.tracing.validator import validate_run


class FakeRuntime:
    def __init__(
        self,
        *,
        tools: list[McpToolDefinition] | None = None,
        call_error: McpRuntimeError | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.tools = tools or [McpToolDefinition(name="read_file")]
        self.call_error = call_error
        self.close_error = close_error
        self.closed = False
        self.calls: list[tuple[str, Any]] = []

    def connect(self) -> McpConnectionInfo:
        self.calls.append(("connect", None))
        return McpConnectionInfo(
            transport="stdio",
            server_name="filesystem",
            server_command="mcp-filesystem",
            server_args=["."],
        )

    def initialize(self) -> McpSessionInfo:
        self.calls.append(("initialize", None))
        return McpSessionInfo(protocol_version="2024-11-05", capabilities={"tools": True})

    def list_tools(self) -> list[McpToolDefinition]:
        self.calls.append(("list_tools", None))
        return self.tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult:
        self.calls.append(("call_tool", {"name": name, "arguments": arguments}))
        if self.call_error is not None:
            raise self.call_error
        return McpToolCallResult(
            tool_name=name,
            arguments=arguments,
            content=[{"type": "text", "text": "# LumiAgent"}],
            latency_ms=7,
        )

    def close(self) -> None:
        self.calls.append(("close", None))
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


def test_capture_config_rejects_non_dict_arguments() -> None:
    with pytest.raises(ValidationError):
        McpCaptureConfig(
            server_command="mcp-filesystem",
            tool_name="read_file",
            arguments=[("path", "README.md")],
        )


def test_capture_config_rejects_non_stdio_transport() -> None:
    with pytest.raises(ValidationError):
        McpCaptureConfig(
            transport="http",
            server_command="mcp-filesystem",
            tool_name="read_file",
        )


def test_capture_config_rejects_blank_server_command() -> None:
    with pytest.raises(ValidationError):
        McpCaptureConfig(
            server_command="   ",
            tool_name="read_file",
        )


def test_capture_config_rejects_blank_tool_name() -> None:
    with pytest.raises(ValidationError):
        McpCaptureConfig(
            server_command="mcp-filesystem",
            tool_name="   ",
        )


def test_capture_config_rejects_invalid_timeout_seconds() -> None:
    with pytest.raises(ValidationError):
        McpCaptureConfig(
            server_command="mcp-filesystem",
            tool_name="read_file",
            timeout_seconds=0,
        )


def test_capture_strategy_captures_success_trace_and_closes_runtime() -> None:
    runtime = FakeRuntime()
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            server_command="mcp-filesystem",
            server_args=["."],
            tool_name="read_file",
            arguments={"path": "README.md"},
            server_name="filesystem",
        ),
        runtime=runtime,
    )

    run = strategy.capture()

    validate_run(run)
    assert run.status is RunStatus.SUCCESS
    assert run.output == {"tool_name": "read_file", "is_error": False}
    assert runtime.closed is True
    assert runtime.calls == [
        ("connect", None),
        ("initialize", None),
        ("list_tools", None),
        ("call_tool", {"name": "read_file", "arguments": {"path": "README.md"}}),
        ("close", None),
    ]


def test_capture_strategy_suppresses_close_error_after_success_trace() -> None:
    runtime = FakeRuntime(close_error=RuntimeError("close failed"))
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            server_command="mcp-filesystem",
            tool_name="read_file",
            arguments={"path": "README.md"},
        ),
        runtime=runtime,
    )

    run = strategy.capture()

    validate_run(run)
    assert run.status is RunStatus.SUCCESS
    assert run.output == {"tool_name": "read_file", "is_error": False}
    assert runtime.closed is True
    assert runtime.calls[-1] == ("close", None)


def test_capture_strategy_suppresses_close_error_after_primary_runtime_error() -> None:
    runtime = FakeRuntime(
        call_error=McpRuntimeError(
            failure_type=McpFailureType.TOOL_EXECUTION_FAILED,
            stage=McpRuntimeStage.TOOL_EXECUTION,
            message="tool call failed",
        ),
        close_error=RuntimeError("close failed"),
    )
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            server_command="mcp-filesystem",
            tool_name="read_file",
            arguments={"path": "README.md"},
        ),
        runtime=runtime,
    )

    run = strategy.capture()

    validate_run(run)
    assert run.status is RunStatus.ERROR
    assert run.output == {"status": "error", "failure_type": "tool_execution_failed"}
    assert run.diagnoses[0].failure_type == "tool_execution_failed"
    assert runtime.closed is True
    assert runtime.calls[-1] == ("close", None)


def test_capture_strategy_captures_tool_not_found_error_trace() -> None:
    runtime = FakeRuntime(tools=[McpToolDefinition(name="write_file")])
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            server_command="mcp-filesystem",
            tool_name="read_file",
            arguments={"path": "README.md"},
        ),
        runtime=runtime,
    )

    run = strategy.capture()

    validate_run(run)
    assert run.status is RunStatus.ERROR
    assert run.output == {"status": "error", "failure_type": "tool_not_found"}
    assert run.diagnoses[0].failure_type == "tool_not_found"
    assert runtime.closed is True
    assert [call[0] for call in runtime.calls] == ["connect", "initialize", "list_tools", "close"]
