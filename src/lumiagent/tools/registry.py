"""Tool registry - manages tool registration, discovery, and execution."""
from __future__ import annotations

import time
from typing import Any

from lumiagent.logging import get_logger
from lumiagent.models.llm import ToolSchema
from lumiagent.models.tool import ToolResult, ToolResultStatus
from lumiagent.tools.base import BaseTool

logger = get_logger(__name__)


class ToolRegistry:
    """Central registry for all tools (built-in and MCP)."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            logger.warning("Overwriting existing tool", tool=tool.name)
        self._tools[tool.name] = tool
        logger.info("Tool registered", tool=tool.name)

    def unregister(self, name: str) -> None:
        if name in self._tools:
            del self._tools[name]
            logger.info("Tool unregistered", tool=name)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> list[ToolSchema]:
        return [
            ToolSchema(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
            )
            for tool in self._tools.values()
        ]

    async def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.ERROR,
                error=f"Tool '{tool_name}' not found. Available: {', '.join(self._tools.keys())}",
            )

        t0 = time.monotonic()
        try:
            result = await tool.execute(**kwargs)
            result.execution_ms = (time.monotonic() - t0) * 1000
            logger.debug("Tool executed", tool=tool_name, ms=result.execution_ms)
            return result
        except Exception as e:
            elapsed = (time.monotonic() - t0) * 1000
            logger.exception("Tool execution failed", tool=tool_name)
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.ERROR,
                error=str(e),
                execution_ms=elapsed,
            )

    def register_defaults(self) -> None:
        """Register all built-in tools."""
        from lumiagent.tools.builtin.bash_tool import BashTool
        from lumiagent.tools.builtin.file_tools import ReadFileTool, WriteFileTool, ListDirTool
        from lumiagent.tools.builtin.web_tools import WebSearchTool, WebFetchTool
        from lumiagent.tools.builtin.python_exec import PythonExecTool
        from lumiagent.tools.builtin.cron_tool import CronTool

        defaults = [
            BashTool(),
            ReadFileTool(),
            WriteFileTool(),
            ListDirTool(),
            WebSearchTool(),
            WebFetchTool(),
            PythonExecTool(),
            CronTool(),
        ]
        for tool in defaults:
            self.register(tool)
