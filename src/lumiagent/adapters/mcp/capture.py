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
        run: AgentRun | None = None
        primary_error: BaseException | None = None
        try:
            connection = self.runtime.connect()
            session = self.runtime.initialize()
            tools = self.runtime.list_tools()
            selection = self.selector.select(
                requested_tool_name=self.config.tool_name,
                tools=tools,
            )
            result = self.runtime.call_tool(selection.selected_tool_name, self.config.arguments)
            run = self.mapper.map_success(
                run_name=self._run_name(),
                connection=connection,
                session=session,
                tools=tools,
                selection=selection,
                result=result,
            )
        except McpRuntimeError as error:
            primary_error = error
            if connection is None:
                raise
            run = self.mapper.map_failure(
                run_name=self._run_name(),
                connection=connection,
                session=session,
                tools=tools or self._fallback_tools(),
                requested_tool_name=self.config.tool_name,
                error=error,
            )
        except Exception as error:
            primary_error = error
            raise
        finally:
            try:
                self.runtime.close()
            except Exception as close_exc:
                if run is not None:
                    pass
                elif primary_error is not None:
                    raise primary_error from close_exc
                else:
                    raise close_exc

        if run is None:
            raise RuntimeError("MCP capture did not produce a trace")
        return run

    def _run_name(self) -> str:
        server_name = self.config.server_name or self.config.server_command
        return f"MCP capture {server_name}.{self.config.tool_name}"

    def _fallback_tools(self) -> list[McpToolDefinition]:
        return [McpToolDefinition(name=self.config.tool_name)]
