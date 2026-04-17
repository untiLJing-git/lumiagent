"""Complete RAG pipeline: ingest → retrieve → rerank."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lumiagent.config import RAGConfig
from lumiagent.logging import get_logger
from lumiagent.rag.embedder import Embedder, OpenAIEmbedder
from lumiagent.rag.loader import DocumentLoader
from lumiagent.rag.reranker import Reranker, SimpleReranker
from lumiagent.rag.splitter import Chunk, TextSplitter
from lumiagent.rag.vector_store import ChromaVectorStore, SearchResult, VectorStore

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    content: str
    source: str
    score: float


class RAGPipeline:
    """End-to-end RAG pipeline."""

    def __init__(
        self,
        config: RAGConfig,
        embedder: Embedder,
        vector_store: Optional[VectorStore] = None,
        reranker: Optional[Reranker] = None,
    ) -> None:
        self.config = config
        self.loader = DocumentLoader()
        self.splitter = TextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        self.embedder = embedder
        self.vector_store = vector_store or ChromaVectorStore(config.chroma_path)
        self.reranker = reranker or SimpleReranker()
        self._initialized = False

    async def initialize(self) -> None:
        if not self._initialized:
            await self.vector_store.initialize()
            self._initialized = True

    async def ingest(self, source: str, collection: str = "default") -> int:
        """Ingest documents from a source into the vector store.
        Returns number of chunks created.
        """
        await self.initialize()

        # Load documents
        documents = await self.loader.load(source)
        logger.info("Loaded documents", source=source, count=len(documents))

        # Split into chunks
        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = self.splitter.split(doc.content, source=doc.source)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("No chunks created from source", source=source)
            return 0

        # Generate embeddings
        texts = [c.content for c in all_chunks]
        embeddings = await self.embedder.embed_batch(texts)

        # Store in vector database
        await self.vector_store.upsert(all_chunks, embeddings, collection=collection)

        logger.info("Ingested documents", source=source, chunks=len(all_chunks))
        return len(all_chunks)

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        collection: str = "default",
    ) -> list[RetrievalResult]:
        """Retrieve relevant chunks for a query."""
        await self.initialize()

        k = top_k or self.config.top_k
        query_embedding = await self.embedder.embed(query)

        # Initial retrieval (fetch more for reranking)
        fetch_k = k * 3 if self.config.rerank_enabled else k
        candidates = await self.vector_store.search(
            query_embedding, top_k=fetch_k, collection=collection
        )

        # Rerank if enabled
        if self.config.rerank_enabled and self.reranker:
            candidates = await self.reranker.rerank(query, candidates, top_k=k)
        else:
            candidates = candidates[:k]

        return [
            RetrievalResult(
                content=r.content,
                source=r.source,
                score=r.score,
            )
            for r in candidates
        ]

    async def delete_knowledge(self, collection: str) -> None:
        """Delete a knowledge collection."""
        await self.initialize()
        await self.vector_store.delete_collection(collection)

    async def list_knowledge(self) -> list[str]:
        """List all knowledge collections."""
        await self.initialize()
        return await self.vector_store.list_collections()
