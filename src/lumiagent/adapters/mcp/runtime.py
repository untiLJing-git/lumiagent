"""Transport-agnostic MCP client runtime interfaces."""
from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from lumiagent.adapters.mcp.taxonomy import McpFailureType
else:
    McpFailureType = __import__(
        "lumiagent.adapters.mcp.taxonomy",
        fromlist=["McpFailureType"],
    ).McpFailureType


class McpRuntimeStage(StrEnum):
    CONNECTION = "connection"
    INITIALIZATION = "initialization"
    TOOL_DISCOVERY = "tool_discovery"
    TOOL_SELECTION = "tool_selection"
    TOOL_EXECUTION = "tool_execution"
    RESULT_PARSING = "result_parsing"


class McpConnectionInfo(BaseModel):
    transport: str
    server_name: str
    server_command: str | None = None
    server_args: list[str] = Field(default_factory=list)

    @field_validator("transport", "server_name")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class McpSessionInfo(BaseModel):
    protocol_version: str | None = None
    server_name: str | None = None
    capabilities: dict[str, Any] = Field(default_factory=dict)


class McpToolDefinition(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool name must not be empty")
        return value


class McpToolCallResult(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    content: list[Any] = Field(default_factory=list)
    is_error: bool = False
    latency_ms: int | None = Field(default=None, ge=0)
    raw_result: Any = None

    @field_validator("tool_name")
    @classmethod
    def require_tool_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool_name must not be empty")
        return value


class McpRuntimeError(Exception):
    def __init__(
        self,
        *,
        failure_type: McpFailureType,
        stage: McpRuntimeStage,
        message: str,
        raw_error_code: str | None = None,
        raw_error_data: Any = None,
    ) -> None:
        super().__init__(message)
        self.failure_type = failure_type
        self.stage = stage
        self.message = message
        self.raw_error_code = raw_error_code
        self.raw_error_data = raw_error_data


class McpClientRuntime(Protocol):
    def connect(self) -> McpConnectionInfo: ...

    def initialize(self) -> McpSessionInfo: ...

    def list_tools(self) -> list[McpToolDefinition]: ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult: ...

    def close(self) -> None: ...


class StdioMcpClientRuntime:
    def __init__(
        self,
        *,
        server_command: str,
        server_args: list[str] | None = None,
        server_name: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        if not server_command.strip():
            raise ValueError("server_command must not be empty")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")

        self.server_command = server_command
        self.server_args = server_args or []
        self.server_name = server_name or server_command
        self.timeout_seconds = timeout_seconds

    def connect(self) -> McpConnectionInfo:
        raise NotImplementedError("Stdio MCP connection is implemented in Task 10")

    def initialize(self) -> McpSessionInfo:
        raise NotImplementedError("Stdio MCP initialization is implemented in Task 10")

    def list_tools(self) -> list[McpToolDefinition]:
        raise NotImplementedError("Stdio MCP tool discovery is implemented in Task 10")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult:
        raise NotImplementedError("Stdio MCP tool execution is implemented in Task 10")

    def close(self) -> None:
        return None
