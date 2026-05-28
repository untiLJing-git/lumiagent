"""Transport-agnostic MCP client runtime interfaces."""
from __future__ import annotations

import asyncio
import time
from contextlib import AsyncExitStack, suppress
from datetime import timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, cast

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from mcp import ClientSession
    from mcp.types import CallToolResult, InitializeResult, ListToolsResult

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
        self._loop: asyncio.AbstractEventLoop | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._connection: McpConnectionInfo | None = None

    def connect(self) -> McpConnectionInfo:
        if self._connection is not None:
            return self._connection
        try:
            self._ensure_no_running_loop(
                failure_type=McpFailureType.CONNECTION_FAILED,
                stage=McpRuntimeStage.CONNECTION,
                operation="connect",
            )
            self._loop = asyncio.new_event_loop()
            self._connection = self._loop.run_until_complete(self._connect_async())
            return self._connection
        except ImportError as exc:
            self.close()
            raise self._map_mcp_import_error(exc) from exc
        except Exception as exc:
            self.close()
            raise self._runtime_error(
                McpFailureType.CONNECTION_FAILED,
                McpRuntimeStage.CONNECTION,
                f"Failed to connect to MCP stdio server {self.server_name!r}: {exc}",
                exc,
            ) from exc

    async def _connect_async(self) -> McpConnectionInfo:
        client_session_type, params_type, stdio_client = self._import_mcp_stdio()

        self._exit_stack = AsyncExitStack()
        params = params_type(command=self.server_command, args=self.server_args)
        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            self._session = await self._exit_stack.enter_async_context(
                client_session_type(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
                )
            )
        except Exception as exc:
            await self._exit_stack.aclose()
            self._exit_stack = None
            raise self._runtime_error(
                McpFailureType.CONNECTION_FAILED,
                McpRuntimeStage.CONNECTION,
                f"Failed to launch MCP stdio server {self.server_name!r}: {exc}",
                exc,
            ) from exc
        return McpConnectionInfo(
            transport="stdio",
            server_name=self.server_name,
            server_command=self.server_command,
            server_args=list(self.server_args),
        )

    def initialize(self) -> McpSessionInfo:
        try:
            result = self._run(self._require_session().initialize())
            return self._to_session_info(cast("InitializeResult", result))
        except McpRuntimeError:
            raise
        except Exception as exc:
            raise self._runtime_error(
                McpFailureType.INITIALIZATION_FAILED,
                McpRuntimeStage.INITIALIZATION,
                f"Failed to initialize MCP server {self.server_name!r}: {exc}",
                exc,
            ) from exc

    def list_tools(self) -> list[McpToolDefinition]:
        try:
            result = cast("ListToolsResult", self._run(self._require_session().list_tools()))
            try:
                return [
                    McpToolDefinition(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=dict(tool.inputSchema),
                    )
                    for tool in result.tools
                ]
            except Exception as exc:
                raise self._runtime_error(
                    McpFailureType.RESULT_INVALID,
                    McpRuntimeStage.RESULT_PARSING,
                    f"MCP tool list result shape is invalid: {exc}",
                    exc,
                ) from exc
        except McpRuntimeError:
            raise
        except Exception as exc:
            raise self._runtime_error(
                McpFailureType.TOOL_DISCOVERY_FAILED,
                McpRuntimeStage.TOOL_DISCOVERY,
                f"Failed to list MCP tools from {self.server_name!r}: {exc}",
                exc,
            ) from exc

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolCallResult:
        started = time.monotonic()
        try:
            result = cast(
                "CallToolResult",
                self._run(
                    self._require_session().call_tool(
                        name,
                        arguments,
                        read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
                    )
                ),
            )
            return self._to_tool_result(name, arguments, result, started)
        except McpRuntimeError:
            raise
        except TimeoutError as exc:
            raise self._runtime_error(
                McpFailureType.TIMEOUT,
                McpRuntimeStage.TOOL_EXECUTION,
                f"MCP tool {name!r} timed out.",
                exc,
            ) from exc
        except Exception as exc:
            failure_type = self._classify_error(exc)
            raise self._runtime_error(
                failure_type,
                McpRuntimeStage.TOOL_EXECUTION,
                f"MCP tool {name!r} failed: {exc}",
                exc,
            ) from exc

    def close(self) -> None:
        if self._loop is not None and self._exit_stack is not None:
            self._ensure_no_running_loop(
                failure_type=McpFailureType.CONNECTION_FAILED,
                stage=McpRuntimeStage.CONNECTION,
                operation="close",
            )
            try:
                self._loop.run_until_complete(self._exit_stack.aclose())
            finally:
                self._exit_stack = None
                self._session = None
                self._connection = None
        if self._loop is not None:
            if self._loop.is_closed():
                self._loop = None
                return
            self._loop.close()
            self._loop = None

    def _run(self, awaitable: Any) -> Any:
        if self._loop is None:
            self.connect()
        if self._loop is None:
            raise self._runtime_error(
                McpFailureType.TRANSPORT_INTERRUPTED,
                McpRuntimeStage.CONNECTION,
                "MCP stdio transport is not connected.",
            )
        try:
            return self._run_awaitable(awaitable, McpFailureType.TOOL_EXECUTION_FAILED)
        except TimeoutError:
            raise
        except (BrokenPipeError, EOFError) as exc:
            raise self._runtime_error(
                McpFailureType.TRANSPORT_INTERRUPTED,
                McpRuntimeStage.CONNECTION,
                f"MCP stdio transport closed unexpectedly: {exc}",
                exc,
            ) from exc

    def _require_session(self) -> ClientSession:
        if self._session is None:
            self.connect()
        if self._session is None:
            raise self._runtime_error(
                McpFailureType.TRANSPORT_INTERRUPTED,
                McpRuntimeStage.CONNECTION,
                "MCP stdio session is unavailable.",
            )
        return self._session

    def _to_session_info(self, result: InitializeResult) -> McpSessionInfo:
        try:
            capabilities = result.capabilities.model_dump(by_alias=True, exclude_none=True)
            return McpSessionInfo(
                protocol_version=str(result.protocolVersion),
                server_name=result.serverInfo.name,
                capabilities=capabilities,
            )
        except Exception as exc:
            raise self._runtime_error(
                McpFailureType.RESULT_INVALID,
                McpRuntimeStage.INITIALIZATION,
                f"MCP initialize result shape is invalid: {exc}",
                exc,
            ) from exc

    def _to_tool_result(
        self,
        name: str,
        arguments: dict[str, Any],
        result: CallToolResult,
        started: float,
    ) -> McpToolCallResult:
        try:
            content = [item.model_dump(by_alias=True, exclude_none=True) for item in result.content]
            raw_result = result.model_dump(by_alias=True, exclude_none=True)
            return McpToolCallResult(
                tool_name=name,
                arguments=arguments,
                content=content,
                is_error=result.isError,
                latency_ms=max(0, round((time.monotonic() - started) * 1000)),
                raw_result=raw_result,
            )
        except Exception as exc:
            raise self._runtime_error(
                McpFailureType.RESULT_INVALID,
                McpRuntimeStage.RESULT_PARSING,
                f"MCP tool {name!r} result shape is invalid: {exc}",
                exc,
            ) from exc

    def _map_mcp_import_error(self, exc: ImportError) -> McpRuntimeError:
        return self._runtime_error(
            McpFailureType.CONNECTION_FAILED,
            McpRuntimeStage.CONNECTION,
            "MCP SDK is required for stdio runtime. Install the declared 'mcp' package dependency.",
            exc,
        )

    def _import_mcp_stdio(self) -> tuple[Any, Any, Any]:
        try:
            from mcp import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client
        except ImportError as exc:
            raise self._map_mcp_import_error(exc) from exc
        return ClientSession, StdioServerParameters, stdio_client

    def _ensure_no_running_loop(
        self,
        *,
        failure_type: McpFailureType,
        stage: McpRuntimeStage,
        operation: str,
    ) -> None:
        with suppress(RuntimeError):
            asyncio.get_running_loop()
            raise self._runtime_error(
                failure_type,
                stage,
                (
                    f"Sync MCP stdio runtime {operation} cannot be used inside a running "
                    "event loop; use the async MCP SDK directly instead."
                ),
            )

    def _run_awaitable(self, awaitable: Any, failure_type: McpFailureType) -> Any:
        self._ensure_no_running_loop(
            failure_type=failure_type,
            stage=McpRuntimeStage.TOOL_EXECUTION,
            operation="call",
        )
        if self._loop is None:
            raise self._runtime_error(
                McpFailureType.TRANSPORT_INTERRUPTED,
                McpRuntimeStage.CONNECTION,
                "MCP stdio transport is not connected.",
            )
        return self._loop.run_until_complete(awaitable)

    def _classify_error(self, exc: Exception) -> McpFailureType:
        error_name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        combined = f"{error_name} {message}"
        if any(
            marker in combined
            for marker in (
                "timeout",
                "timed out",
                "timeoutcancellationerror",
                "cancelled",
                "canceled",
            )
        ):
            return McpFailureType.TIMEOUT
        if any(
            marker in combined
            for marker in (
                "permission denied",
                "permission required",
                "unauthorized",
                "forbidden",
                "access denied",
            )
        ):
            return McpFailureType.PERMISSION_DENIED
        if any(
            marker in combined
            for marker in (
                "eof",
                "broken pipe",
                "closed stream",
                "stream closed",
                "connection reset",
                "transport closed",
            )
        ):
            return McpFailureType.TRANSPORT_INTERRUPTED
        if any(marker in combined for marker in ("malformed", "invalid result", "result shape")):
            return McpFailureType.RESULT_INVALID
        return McpFailureType.TOOL_EXECUTION_FAILED

    def _runtime_error(
        self,
        failure_type: McpFailureType,
        stage: McpRuntimeStage,
        message: str,
        exc: Exception | None = None,
    ) -> McpRuntimeError:
        raw_error_code = exc.__class__.__name__ if exc is not None else None
        raw_error_data = {"error": str(exc)} if exc is not None else None
        return McpRuntimeError(
            failure_type=failure_type,
            stage=stage,
            message=message,
            raw_error_code=raw_error_code,
            raw_error_data=raw_error_data,
        )
