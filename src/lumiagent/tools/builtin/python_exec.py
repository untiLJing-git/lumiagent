"""Python code execution tool (sandboxed via subprocess)."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

from lumiagent.models.tool import ToolResult, ToolResultStatus
from lumiagent.tools.base import BaseTool


class PythonExecTool(BaseTool):
    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return "Execute a Python code snippet and return the output. Code runs in a subprocess."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
            },
            "required": ["code"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        code = kwargs.get("code", "")
        timeout = kwargs.get("timeout", 30)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return ToolResult(tool_name=self.name, output=output or "(no output)")
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolResultStatus.ERROR,
                    output=output,
                    error=errors,
                )

        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.TIMEOUT,
                error=f"Execution timed out after {timeout}s",
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
