"""MCP tool selection helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from lumiagent.adapters.mcp.taxonomy import McpFailureType

if TYPE_CHECKING:
    from lumiagent.adapters.mcp.runtime import McpToolDefinition


class McpToolSelection(BaseModel):
    requested_tool_name: str
    selected_tool_name: str
    available_tool_names: list[str] = Field(default_factory=list)
    selection_strategy: str = "explicit"
    reason: str = "Tool name was provided by CLI."

    @field_validator("requested_tool_name", "selected_tool_name", "selection_strategy", "reason")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class ExplicitToolSelector:
    def select(
        self,
        *,
        requested_tool_name: str,
        tools: list[McpToolDefinition],
    ) -> McpToolSelection:
        available_tool_names = [tool.name for tool in tools]
        if requested_tool_name not in available_tool_names:
            raise ValueError(
                f"{McpFailureType.TOOL_NOT_FOUND.value}: requested tool "
                f"{requested_tool_name!r} is not available"
            )
        return McpToolSelection(
            requested_tool_name=requested_tool_name,
            selected_tool_name=requested_tool_name,
            available_tool_names=available_tool_names,
        )
