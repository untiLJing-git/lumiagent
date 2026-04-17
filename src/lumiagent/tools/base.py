"""Base tool interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lumiagent.models.tool import ToolResult


class BaseTool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for LLM."""

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments."""

    def get_schema(self) -> dict[str, Any]:
        """Get the complete tool schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
