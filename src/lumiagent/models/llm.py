"""LLM request/response models."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = ""
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: str  # JSON string


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMRequest(BaseModel):
    messages: list[ChatMessage]
    tools: Optional[list[ToolSchema]] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    stop: Optional[list[str]] = None
    response_format: Optional[dict[str, str]] = None
    model_override: Optional[str] = None


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = "stop"
    latency_ms: float = 0.0

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMChunk(BaseModel):
    delta_content: str = ""
    delta_tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: Optional[str] = None
