"""LLM router with fallback, cost-based, and round-robin strategies."""
from __future__ import annotations

from enum import Enum

from lumiagent.config import Settings
from lumiagent.logging import get_logger
from lumiagent.llm.base import LLMProvider
from lumiagent.llm.openai_provider import OpenAIProvider
from lumiagent.llm.anthropic_provider import AnthropicProvider
from lumiagent.models.llm import LLMRequest, LLMResponse

logger = get_logger(__name__)


class RouteStrategy(str, Enum):
    PRIMARY = "primary"
    COST = "cost"
    QUALITY = "quality"
    ROUND_ROBIN = "round_robin"


class LLMRouter:
    """Routes LLM requests to appropriate providers with fallback."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, LLMProvider] = {}
        self._rr_index = 0
        self._init_providers()

    def _init_providers(self) -> None:
        s = self._settings

        if s.openai_api_key:
            self._providers["openai"] = OpenAIProvider(
                api_key=s.openai_api_key,
                model=s.openai_model,
                base_url=s.openai_base_url,
                provider_label="openai",
            )

        if s.anthropic_api_key:
            self._providers["anthropic"] = AnthropicProvider(
                api_key=s.anthropic_api_key,
                model=s.anthropic_model,
            )

        if s.deepseek_api_key:
            self._providers["deepseek"] = OpenAIProvider(
                api_key=s.deepseek_api_key,
                model=s.deepseek_model,
                base_url=s.deepseek_base_url,
                provider_label="deepseek",
            )

        logger.info("LLM providers initialized", providers=list(self._providers.keys()))

    def get_provider(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' not configured or missing API key")
        return self._providers[name]

    @property
    def primary(self) -> LLMProvider:
        return self.get_provider(self._settings.primary_llm_provider)

    async def chat(
        self,
        request: LLMRequest,
        strategy: RouteStrategy = RouteStrategy.PRIMARY,
    ) -> LLMResponse:
        if strategy == RouteStrategy.PRIMARY:
            return await self._primary_with_fallback(request)
        elif strategy == RouteStrategy.ROUND_ROBIN:
            return await self._round_robin(request)
        elif strategy == RouteStrategy.QUALITY:
            return await self._quality_route(request)
        else:
            return await self._primary_with_fallback(request)

    async def _primary_with_fallback(self, request: LLMRequest) -> LLMResponse:
        primary_name = self._settings.primary_llm_provider
        fallback_name = self._settings.fallback_llm_provider

        try:
            provider = self.get_provider(primary_name)
            response = await provider.chat(request)
            logger.debug("LLM response", provider=primary_name, tokens=response.usage.total_tokens)
            return response
        except Exception:
            logger.warning("Primary LLM failed, trying fallback", primary=primary_name)

        if fallback_name and fallback_name in self._providers:
            try:
                provider = self.get_provider(fallback_name)
                response = await provider.chat(request)
                logger.info("Fallback LLM succeeded", provider=fallback_name)
                return response
            except Exception:
                logger.exception("Fallback LLM also failed", fallback=fallback_name)

        raise RuntimeError("All LLM providers failed")

    async def _round_robin(self, request: LLMRequest) -> LLMResponse:
        names = list(self._providers.keys())
        if not names:
            raise RuntimeError("No LLM providers configured")
        name = names[self._rr_index % len(names)]
        self._rr_index += 1
        return await self._providers[name].chat(request)

    async def _quality_route(self, request: LLMRequest) -> LLMResponse:
        # Prefer strongest available model
        for name in ["anthropic", "openai", "deepseek"]:
            if name in self._providers:
                return await self._providers[name].chat(request)
        raise RuntimeError("No LLM providers configured")
