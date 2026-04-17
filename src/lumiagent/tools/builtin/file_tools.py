"""File operation tools: read, write, list directory."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import aiofiles

from lumiagent.models.tool import ToolResult, ToolResultStatus
from lumiagent.tools.base import BaseTool


class ReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Returns the file text content."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "offset": {"type": "integer", "description": "Line number to start reading from (1-based)"},
                "limit": {"type": "integer", "description": "Maximum number of lines to read"},
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit", 500)

        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                lines = await f.readlines()

            start = max(0, offset - 1)
            end = start + limit
            selected = lines[start:end]
            content = "".join(f"{start + i + 1}\t{line}" for i, line in enumerate(selected))

            return ToolResult(
                tool_name=self.name,
                output=content or "(empty file)",
                metadata={"total_lines": len(lines)},
            )
        except FileNotFoundError:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error=str(e),
            )


class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
                "append": {"type": "boolean", "description": "Append instead of overwrite (default: false)"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        append = kwargs.get("append", False)

        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            async with aiofiles.open(path, mode, encoding="utf-8") as f:
                await f.write(content)

            return ToolResult(
                tool_name=self.name,
                output=f"Written {len(content)} chars to {path}",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error=str(e),
            )


class ListDirTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "List files and directories in a given path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list (default: current dir)"},
                "recursive": {"type": "boolean", "description": "List recursively (default: false)"},
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", ".")
        recursive = kwargs.get("recursive", False)

        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolResultStatus.ERROR,
                    error=f"Directory not found: {path}",
                )

            entries = []
            if recursive:
                for item in sorted(p.rglob("*")):
                    rel = item.relative_to(p)
                    suffix = "/" if item.is_dir() else ""
                    entries.append(f"{rel}{suffix}")
            else:
                for item in sorted(p.iterdir()):
                    suffix = "/" if item.is_dir() else ""
                    entries.append(f"{item.name}{suffix}")

            return ToolResult(
                tool_name=self.name,
                output="\n".join(entries[:200]) or "(empty directory)",
                metadata={"count": len(entries)},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error=str(e),
            )
