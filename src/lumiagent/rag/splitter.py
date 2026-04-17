"""Text splitters for chunking documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lumiagent.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    content: str
    source: str
    chunk_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class TextSplitter:
    """Recursive character text splitter with overlap."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def split(self, text: str, source: str = "") -> list[Chunk]:
        """Split text into overlapping chunks."""
        chunks = self._recursive_split(text, self.separators)
        return [
            Chunk(content=chunk, source=source, chunk_index=i)
            for i, chunk in enumerate(chunks)
            if chunk.strip()
        ]

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        if not separators:
            # Force split by character limit
            return self._split_by_size(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep:
            parts = text.split(sep)
        else:
            return self._split_by_size(text)

        chunks = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(part) > self.chunk_size:
                    chunks.extend(self._recursive_split(part, remaining_seps))
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current)

        # Add overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _split_by_size(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start = end - self.chunk_overlap if self.chunk_overlap else end
        return chunks

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-self.chunk_overlap:]
            result.append(prev_tail + chunks[i])
        return result


class MarkdownSplitter(TextSplitter):
    """Split by Markdown headers."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "],
        )
