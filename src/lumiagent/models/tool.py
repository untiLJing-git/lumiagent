"""Tool system models."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ToolResult(BaseModel):
    tool_name: str
    status: ToolResultStatus = ToolResultStatus.SUCCESS
    output: str = ""
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_ms: float = 0.0


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
