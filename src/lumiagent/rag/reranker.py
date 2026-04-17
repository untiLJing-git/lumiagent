"""Reranker for improving retrieval quality."""
from __future__ import annotations

from abc import ABC, abstractmethod

from lumiagent.logging import get_logger
from lumiagent.rag.vector_store import SearchResult

logger = get_logger(__name__)


class Reranker(ABC):
    """Abstract reranker interface."""

    @abstractmethod
    async def rerank(
        self, query: str, results: list[SearchResult], top_k: int = 5
    ) -> list[SearchResult]: ...


class LLMReranker(Reranker):
    """Reranker using LLM to score relevance."""

    def __init__(self, llm_chat_fn=None) -> None:
        self._llm_chat = llm_chat_fn

    async def rerank(
        self, query: str, results: list[SearchResult], top_k: int = 5
    ) -> list[SearchResult]:
        if not self._llm_chat or len(results) <= top_k:
            return results[:top_k]

        # Use LLM to score each result's relevance
        from lumiagent.models.llm import ChatMessage, ChatRole, LLMRequest

        scored = []
        for r in results:
            prompt = (
                f"Rate the relevance of the following text to the query on a scale of 0-10.\n"
                f"Query: {query}\n"
                f"Text: {r.content[:500]}\n"
                f"Reply with ONLY a number 0-10."
            )
            try:
                response = await self._llm_chat(LLMRequest(
                    messages=[ChatMessage(role=ChatRole.USER, content=prompt)],
                    max_tokens=10,
                    temperature=0.0,
                ))
                score = float(response.content.strip())
                scored.append((score, r))
            except (ValueError, Exception):
                scored.append((r.score * 10, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]


class SimpleReranker(Reranker):
    """Simple keyword-based reranker (no LLM needed)."""

    async def rerank(
        self, query: str, results: list[SearchResult], top_k: int = 5
    ) -> list[SearchResult]:
        query_terms = set(query.lower().split())

        scored = []
        for r in results:
            content_lower = r.content.lower()
            keyword_hits = sum(1 for term in query_terms if term in content_lower)
            combined_score = r.score * 0.7 + (keyword_hits / max(len(query_terms), 1)) * 0.3
            scored.append((combined_score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]
