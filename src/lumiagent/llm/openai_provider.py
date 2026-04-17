"""OpenAI-compatible LLM provider (also works with DeepSeek, Qwen, etc.)."""
from __future__ import annotations

import json
import time
from typing import AsyncIterator

import tiktoken
from openai import AsyncOpenAI

from lumiagent.logging import get_logger
from lumiagent.models.llm import (
    ChatMessage,
    LLMChunk,
    LLMRequest,
    LLMResponse,
    TokenUsage,
    ToolCall,
    ToolSchema,
)
from lumiagent.llm.base import LLMProvider

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI and OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
        provider_label: str = "openai",
    ) -> None:
        self._model = model
        self._label = provider_label
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    @property
    def provider_name(self) -> str:
        return self._label

    @property
    def supported_models(self) -> list[str]:
        return [self._model]

    def _build_messages(self, messages: list[ChatMessage]) -> list[dict]:
        result = []
        for msg in messages:
            d: dict = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                d["name"] = msg.name
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            result.append(d)
        return result

    def _build_tools(self, tools: list[ToolSchema]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    async def chat(self, request: LLMRequest) -> LLMResponse:
        model = request.model_override or self._model
        t0 = time.monotonic()

        kwargs: dict = {
            "model": model,
            "messages": self._build_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            kwargs["tools"] = self._build_tools(request.tools)
        if request.stop:
            kwargs["stop"] = request.stop
        if request.response_format:
            kwargs["response_format"] = request.response_format

        response = await self._client.chat.completions.create(**kwargs)
        elapsed = (time.monotonic() - t0) * 1000

        choice = response.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                )
                for tc in choice.message.tool_calls
            ]

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
            finish_reason=choice.finish_reason or "stop",
            latency_ms=elapsed,
        )

    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        model = request.model_override or self._model

        kwargs: dict = {
            "model": model,
            "messages": self._build_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.tools:
            kwargs["tools"] = self._build_tools(request.tools)

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            yield LLMChunk(
                delta_content=delta.content or "",
                finish_reason=chunk.choices[0].finish_reason,
            )

    def count_tokens(self, messages: list[ChatMessage]) -> int:
        count = 0
        for msg in messages:
            count += 4  # message overhead
            count += len(self._encoding.encode(msg.content))
            if msg.name:
                count += len(self._encoding.encode(msg.name))
        count += 2  # reply priming
        return count
