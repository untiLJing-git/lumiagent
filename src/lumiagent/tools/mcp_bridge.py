"""MCP (Model Context Protocol) tool bridge for hot-pluggable external tools."""
from __future__ import annotations

import asyncio
from typing import Any

from lumiagent.logging import get_logger
from lumiagent.models.llm import ToolSchema
from lumiagent.models.tool import MCPServerConfig, ToolResult, ToolResultStatus
from lumiagent.tools.base import BaseTool
from lumiagent.tools.registry import ToolRegistry

logger = get_logger(__name__)


class MCPToolWrapper(BaseTool):
    """Wraps an MCP server tool as a local BaseTool."""

    def __init__(
        self,
        tool_name: str,
        tool_description: str,
        tool_parameters: dict[str, Any],
        server_name: str,
        call_fn,
    ) -> None:
        self._name = tool_name
        self._description = tool_description
        self._parameters = tool_parameters
        self._server_name = server_name
        self._call_fn = call_fn

    @property
    def name(self) -> str:
        return f"mcp_{self._server_name}_{self._name}"

    @property
    def description(self) -> str:
        return f"[MCP: {self._server_name}] {self._description}"

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = await self._call_fn(self._name, kwargs)
            return ToolResult(
                tool_name=self.name,
                output=str(result),
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error=str(e),
            )


class MCPBridge:
    """Manages connections to MCP servers and bridges their tools."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._servers: dict[str, Any] = {}  # server_name -> client session
        self._server_tools: dict[str, list[str]] = {}  # server_name -> tool names

    async def connect(self, config: MCPServerConfig) -> int:
        """Connect to an MCP server, discover tools, and register them.
        Returns number of tools discovered.
        """
        logger.info("Connecting to MCP server", server=config.name, command=config.command)

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env={**config.env} if config.env else None,
            )

            # Note: actual connection requires context manager usage
            # This is a simplified version - full impl needs session management
            logger.info("MCP server connected (stub)", server=config.name)

            # In production, iterate over session.list_tools() and register each
            self._servers[config.name] = None  # placeholder
            self._server_tools[config.name] = []
            return 0

        except ImportError:
            logger.warning("MCP SDK not installed, skipping", server=config.name)
            return 0
        except Exception:
            logger.exception("Failed to connect MCP server", server=config.name)
            return 0

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server and unregister its tools."""
        tool_names = self._server_tools.pop(server_name, [])
        for name in tool_names:
            self._registry.unregister(name)
        self._servers.pop(server_name, None)
        logger.info("MCP server disconnected", server=server_name, tools_removed=len(tool_names))

    async def hot_reload(self, configs: list[MCPServerConfig]) -> None:
        """Reload MCP servers based on updated config."""
        desired = {c.name for c in configs if c.enabled}
        current = set(self._servers.keys())

        # Remove servers no longer in config
        for name in current - desired:
            await self.disconnect(name)

        # Add new servers
        for config in configs:
            if config.enabled and config.name not in current:
                await self.connect(config)
