"""Bash command execution tool."""
from __future__ import annotations

import asyncio
from typing import Any

from lumiagent.models.tool import ToolResult, ToolResultStatus
from lumiagent.tools.base import BaseTool


class BashTool(BaseTool):
    def __init__(self, timeout: int = 30) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a shell command and return stdout/stderr. Use for system operations, file management, and running programs."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {self._timeout})",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory for the command",
                },
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", self._timeout)
        workdir = kwargs.get("workdir")

        if not command:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error="No command provided",
            )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return ToolResult(
                    tool_name=self.name,
                    output=output or "(no output)",
                    metadata={"return_code": process.returncode},
                )
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolResultStatus.ERROR,
                    output=output,
                    error=errors or f"Exit code: {process.returncode}",
                    metadata={"return_code": process.returncode},
                )

        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.TIMEOUT,
                error=f"Command timed out after {timeout}s",
            )
