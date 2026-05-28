import asyncio

import pytest
from pydantic import ValidationError

from lumiagent.adapters.mcp.runtime import (
    McpClientRuntime,
    McpConnectionInfo,
    McpRuntimeError,
    McpRuntimeStage,
    McpSessionInfo,
    McpToolCallResult,
    McpToolDefinition,
    StdioMcpClientRuntime,
)
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_runtime_protocol_is_public() -> None:
    assert McpClientRuntime.__name__ == "McpClientRuntime"


def test_runtime_data_models_capture_transport_and_tool_result() -> None:
    connection = McpConnectionInfo(
        transport="stdio",
        server_name="filesystem",
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "."],
    )
    session = McpSessionInfo(protocol_version="2024-11-05", server_name="filesystem")
    tool = McpToolDefinition(
        name="read_file",
        description="Read a file",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
    )
    result = McpToolCallResult(
        tool_name="read_file",
        arguments={"path": "README.md"},
        content=[{"type": "text", "text": "# LumiAgent"}],
        is_error=False,
        latency_ms=12,
    )

    assert connection.transport == "stdio"
    assert session.server_name == "filesystem"
    assert tool.name == "read_file"
    assert result.content[0]["type"] == "text"


def test_runtime_error_carries_failure_type_and_stage() -> None:
    error = McpRuntimeError(
        failure_type=McpFailureType.TOOL_NOT_FOUND,
        stage=McpRuntimeStage.TOOL_SELECTION,
        message="Tool read_me was not found.",
        raw_error_code="tool_not_found",
        raw_error_data={"available_tools": ["read_file"]},
    )

    assert error.failure_type is McpFailureType.TOOL_NOT_FOUND
    assert error.stage is McpRuntimeStage.TOOL_SELECTION
    assert error.raw_error_data == {"available_tools": ["read_file"]}


def test_tool_definition_requires_name() -> None:
    with pytest.raises(ValidationError):
        McpToolDefinition(name="", input_schema={})


def test_stdio_runtime_stores_launch_configuration() -> None:
    runtime = StdioMcpClientRuntime(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        server_name="filesystem",
        timeout_seconds=5,
    )

    assert runtime.server_command == "npx"
    assert runtime.server_args == ["-y", "@modelcontextprotocol/server-filesystem", "."]
    assert runtime.server_name == "filesystem"
    assert runtime.timeout_seconds == 5


def test_stdio_runtime_exposes_runtime_methods() -> None:
    runtime = StdioMcpClientRuntime(server_command="npx", server_args=[])

    assert callable(runtime.connect)
    assert callable(runtime.initialize)
    assert callable(runtime.list_tools)
    assert callable(runtime.call_tool)
    assert callable(runtime.close)


def test_stdio_runtime_rejects_blank_server_command() -> None:
    with pytest.raises(ValueError, match="server_command"):
        StdioMcpClientRuntime(server_command="   ")


def test_stdio_runtime_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        StdioMcpClientRuntime(server_command="npx", timeout_seconds=0)


def test_import_failure_maps_to_connection_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StdioMcpClientRuntime(server_command="server")

    def fail_imports() -> None:
        raise ImportError("No module named 'mcp'")

    monkeypatch.setattr(runtime, "_import_mcp_stdio", fail_imports)

    with pytest.raises(McpRuntimeError) as error_info:
        runtime.connect()

    error = error_info.value
    assert error.failure_type is McpFailureType.CONNECTION_FAILED
    assert error.stage is McpRuntimeStage.CONNECTION
    assert "MCP SDK is required" in error.message


def test_sync_stdio_runtime_rejects_running_event_loop() -> None:
    async def run_sync_connect() -> None:
        runtime = StdioMcpClientRuntime(server_command="server")

        with pytest.raises(McpRuntimeError) as error_info:
            runtime.connect()

        error = error_info.value
        assert error.failure_type is McpFailureType.CONNECTION_FAILED
        assert error.stage is McpRuntimeStage.CONNECTION
        assert "cannot be used inside a running event loop" in error.message

    asyncio.run(run_sync_connect())


def test_runtime_classifies_timeout_permission_transport_and_invalid_result() -> None:
    runtime = StdioMcpClientRuntime(server_command="server")

    assert runtime._classify_error(TimeoutError("timed out")) is McpFailureType.TIMEOUT
    assert runtime._classify_error(Exception("TimeoutCancellationError")) is McpFailureType.TIMEOUT
    assert (
        runtime._classify_error(Exception("permission required"))
        is McpFailureType.PERMISSION_DENIED
    )
    assert runtime._classify_error(Exception("Unauthorized")) is McpFailureType.PERMISSION_DENIED
    assert runtime._classify_error(EOFError("EOF")) is McpFailureType.TRANSPORT_INTERRUPTED
    assert runtime._classify_error(Exception("broken pipe")) is McpFailureType.TRANSPORT_INTERRUPTED
    assert (
        runtime._classify_error(Exception("connection reset by peer"))
        is McpFailureType.TRANSPORT_INTERRUPTED
    )
    assert runtime._classify_error(ValueError("malformed result")) is McpFailureType.RESULT_INVALID


def test_list_tools_malformed_tool_maps_to_result_invalid() -> None:
    class BrokenTool:
        name = "broken"
        description = None

    class BrokenListToolsResult:
        tools = [BrokenTool()]

    class FakeSession:
        async def list_tools(self) -> BrokenListToolsResult:
            return BrokenListToolsResult()

    runtime = StdioMcpClientRuntime(server_command="server")
    runtime._loop = asyncio.new_event_loop()
    runtime._session = FakeSession()  # type: ignore[assignment]
    try:
        with pytest.raises(McpRuntimeError) as error_info:
            runtime.list_tools()
    finally:
        runtime.close()

    error = error_info.value
    assert error.failure_type is McpFailureType.RESULT_INVALID
    assert error.stage is McpRuntimeStage.RESULT_PARSING
