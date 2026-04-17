"""Vector store backends for RAG."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from lumiagent.logging import get_logger
from lumiagent.rag.splitter import Chunk

logger = get_logger(__name__)


@dataclass
class SearchResult:
    content: str
    source: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def upsert(
        self, chunks: list[Chunk], embeddings: list[list[float]], collection: str = "default"
    ) -> None: ...

    @abstractmethod
    async def search(
        self, embedding: list[float], top_k: int = 5, collection: str = "default"
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def delete_collection(self, collection: str) -> None: ...

    @abstractmethod
    async def list_collections(self) -> list[str]: ...


class ChromaVectorStore(VectorStore):
    """ChromaDB-based vector store (local, embedded)."""

    def __init__(self, persist_path: str = "./data/chroma") -> None:
        self._persist_path = persist_path
        self._client = None

    async def initialize(self) -> None:
        import chromadb
        from pathlib import Path

        Path(self._persist_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._persist_path)
        logger.info("ChromaDB initialized", path=self._persist_path)

    def _get_collection(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(
        self, chunks: list[Chunk], embeddings: list[list[float]], collection: str = "default"
    ) -> None:
        if not self._client:
            await self.initialize()

        coll = self._get_collection(collection)
        ids = [f"{collection}_{c.source}_{c.chunk_index}" for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [{"source": c.source, "chunk_index": c.chunk_index, **c.metadata} for c in chunks]

        coll.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Upserted chunks", collection=collection, count=len(chunks))

    async def search(
        self, embedding: list[float], top_k: int = 5, collection: str = "default"
    ) -> list[SearchResult]:
        if not self._client:
            await self.initialize()

        coll = self._get_collection(collection)
        results = coll.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                search_results.append(SearchResult(
                    content=doc,
                    source=meta.get("source", ""),
                    score=1.0 - dist,  # Convert distance to similarity
                    metadata=meta,
                ))

        return search_results

    async def delete_collection(self, collection: str) -> None:
        if self._client:
            try:
                self._client.delete_collection(collection)
                logger.info("Deleted collection", collection=collection)
            except Exception:
                logger.warning("Collection not found", collection=collection)

    async def list_collections(self) -> list[str]:
        if not self._client:
            await self.initialize()
        collections = self._client.list_collections()
        return [c.name for c in collections]
