"""Base LLM provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from lumiagent.models.llm import ChatMessage, LLMChunk, LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]: ...

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat completion request."""

    @abstractmethod
    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Stream a chat completion."""

    @abstractmethod
    def count_tokens(self, messages: list[ChatMessage]) -> int:
        """Estimate token count for messages."""
