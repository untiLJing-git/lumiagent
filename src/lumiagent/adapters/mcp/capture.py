"""Orchestrate MCP runtime capture into LumiAgent traces."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lumiagent.adapters.mcp.mapper import McpTraceMapper
from lumiagent.adapters.mcp.runtime import (
    McpClientRuntime,
    McpConnectionInfo,
    McpRuntimeError,
    McpSessionInfo,
    McpToolDefinition,
    StdioMcpClientRuntime,
)
from lumiagent.adapters.mcp.selector import ExplicitToolSelector

if TYPE_CHECKING:
    from lumiagent.tracing import AgentRun


class McpCaptureConfig(BaseModel):
    """Configuration for a single MCP tool capture."""

    model_config = ConfigDict(extra="forbid")

    transport: str = "stdio"
    server_command: str
    server_args: list[str] = Field(default_factory=list)
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_path: str | None = None
    timeout_seconds: int = Field(default=30, ge=1)
    server_name: str | None = None

    @field_validator("transport")
    @classmethod
    def require_stdio_transport(cls, value: str) -> str:
        if value != "stdio":
            raise ValueError("only stdio transport is supported")
        return value

    @field_validator("server_command", "tool_name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class McpCaptureStrategy:
    """Capture one MCP tool call through a runtime, selector, and trace mapper."""

    def __init__(
        self,
        *,
        config: McpCaptureConfig,
        runtime: McpClientRuntime | None = None,
        selector: ExplicitToolSelector | None = None,
        mapper: McpTraceMapper | None = None,
    ) -> None:
        self.config = config
        self.runtime = runtime or StdioMcpClientRuntime(
            server_command=config.server_command,
            server_args=config.server_args,
            server_name=config.server_name,
            timeout_seconds=config.timeout_seconds,
        )
        self.selector = selector or ExplicitToolSelector()
        self.mapper = mapper or McpTraceMapper()

    def capture(self) -> AgentRun:
        connection: McpConnectionInfo | None = None
        session: McpSessionInfo | None = None
        tools: list[McpToolDefinition] = []
        try:
            connection = self.runtime.connect()
            session = self.runtime.initialize()
            tools = self.runtime.list_tools()
            selection = self.selector.select(
                requested_tool_name=self.config.tool_name,
                tools=tools,
            )
            result = self.runtime.call_tool(selection.selected_tool_name, self.config.arguments)
            return self.mapper.map_success(
                run_name=self._run_name(),
                connection=connection,
                session=session,
                tools=tools,
                selection=selection,
                result=result,
            )
        except McpRuntimeError as error:
            return self.mapper.map_failure(
                run_name=self._run_name(),
                connection=connection or self._fallback_connection(),
                session=session,
                tools=tools,
                requested_tool_name=self.config.tool_name,
                error=error,
            )
        finally:
            self.runtime.close()

    def _run_name(self) -> str:
        server_name = self.config.server_name or self.config.server_command
        return f"MCP capture {server_name}.{self.config.tool_name}"

    def _fallback_connection(self) -> McpConnectionInfo:
        return McpConnectionInfo(
            transport=self.config.transport,
            server_name=self.config.server_name or self.config.server_command,
            server_command=self.config.server_command,
            server_args=self.config.server_args,
        )
