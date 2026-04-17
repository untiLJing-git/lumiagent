"""Embedding providers for vectorizing text."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from lumiagent.logging import get_logger

logger = get_logger(__name__)


class Embedder(ABC):
    """Abstract embedding provider."""

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Embed multiple texts, batching API calls."""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_results = [await self.embed(t) for t in batch]
            results.extend(batch_results)
        return results


class OpenAIEmbedder(Embedder):
    """OpenAI embedding provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ) -> None:
        self._model = model
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Dimension lookup
        self._dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    @property
    def dimension(self) -> int:
        return self._dimensions.get(self._model, 1536)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._client.embeddings.create(
                model=self._model,
                input=batch,
            )
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings
