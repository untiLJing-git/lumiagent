"""Anthropic Claude LLM provider."""
from __future__ import annotations

import time
from typing import AsyncIterator

from lumiagent.logging import get_logger
from lumiagent.models.llm import (
    ChatMessage,
    ChatRole,
    LLMChunk,
    LLMRequest,
    LLMResponse,
    TokenUsage,
    ToolCall,
    ToolSchema,
)
from lumiagent.llm.base import LLMProvider

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self._model = model
        self._api_key = api_key
        self._client = None  # Lazy init

    def _ensure_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self._api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> list[str]:
        return [self._model]

    def _extract_system(self, messages: list[ChatMessage]) -> tuple[str, list[dict]]:
        system = ""
        msgs = []
        for msg in messages:
            if msg.role == ChatRole.SYSTEM:
                system += msg.content + "\n"
            elif msg.role == ChatRole.TOOL:
                msgs.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "",
                            "content": msg.content,
                        }
                    ],
                })
            else:
                msgs.append({"role": msg.role.value, "content": msg.content})
        return system.strip(), msgs

    def _build_tools(self, tools: list[ToolSchema]) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    async def chat(self, request: LLMRequest) -> LLMResponse:
        self._ensure_client()
        model = request.model_override or self._model
        system, messages = self._extract_system(request.messages)
        t0 = time.monotonic()

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system:
            kwargs["system"] = system
        if request.tools:
            kwargs["tools"] = self._build_tools(request.tools)

        response = await self._client.messages.create(**kwargs)
        elapsed = (time.monotonic() - t0) * 1000

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                import json
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=json.dumps(block.input),
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            ),
            model=response.model,
            finish_reason=response.stop_reason or "end_turn",
            latency_ms=elapsed,
        )

    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        self._ensure_client()
        model = request.model_override or self._model
        system, messages = self._extract_system(request.messages)

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield LLMChunk(delta_content=text)

    def count_tokens(self, messages: list[ChatMessage]) -> int:
        # Rough estimate: 1 token ≈ 4 chars for Claude
        total = sum(len(m.content) for m in messages)
        return total // 4 + len(messages) * 4
