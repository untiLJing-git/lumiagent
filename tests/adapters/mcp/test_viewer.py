from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
from lumiagent.adapters.mcp.runtime import McpToolDefinition
from lumiagent.adapters.mcp.viewer import render_mcp_trace_summary
from tests.adapters.mcp.test_capture import FakeRuntime


def test_render_success_trace_summary_from_capture_strategy() -> None:
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            server_command="mcp-filesystem",
            server_args=["."],
            tool_name="read_file",
            arguments={"path": "README.md"},
            server_name="filesystem",
        ),
        runtime=FakeRuntime(),
    )

    lines = render_mcp_trace_summary(strategy.capture())
    output = "\n".join(lines)

    assert "Run" in output
    assert "Status: success" in output
    assert "MCP Tool Chain" in output
    assert "Tool Selection" in output
    assert "requested: read_file" in output
    assert "selected: read_file" in output


def test_render_failure_trace_summary_from_capture_strategy() -> None:
    strategy = McpCaptureStrategy(
        config=McpCaptureConfig(
            server_command="mcp-filesystem",
            server_args=["."],
            tool_name="read_me",
            arguments={"path": "README.md"},
            server_name="filesystem",
        ),
        runtime=FakeRuntime(tools=[McpToolDefinition(name="read_file")]),
    )

    lines = render_mcp_trace_summary(strategy.capture())
    output = "\n".join(lines)

    assert "Status: error" in output
    assert "MCP Failure" in output
    assert "type: tool_not_found" in output
    assert "requested tool: read_me" in output
