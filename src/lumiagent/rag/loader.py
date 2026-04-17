"""Document loaders for various file formats."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lumiagent.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Document:
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentLoader:
    """Multi-format document loader."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".html", ".csv", ".json"}

    async def load(self, source: str) -> list[Document]:
        """Load documents from a file path or directory."""
        path = Path(source)

        if path.is_file():
            return [await self._load_file(path)]
        elif path.is_dir():
            docs = []
            for file_path in sorted(path.rglob("*")):
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    try:
                        doc = await self._load_file(file_path)
                        docs.append(doc)
                    except Exception:
                        logger.warning("Failed to load file", path=str(file_path))
            return docs
        else:
            raise FileNotFoundError(f"Source not found: {source}")

    async def _load_file(self, path: Path) -> Document:
        suffix = path.suffix.lower()

        if suffix in (".txt", ".md"):
            return await self._load_text(path)
        elif suffix == ".pdf":
            return await self._load_pdf(path)
        elif suffix == ".docx":
            return await self._load_docx(path)
        elif suffix == ".html":
            return await self._load_html(path)
        elif suffix == ".csv":
            return await self._load_text(path)  # Treat as text
        elif suffix == ".json":
            return await self._load_text(path)
        else:
            return await self._load_text(path)

    async def _load_text(self, path: Path) -> Document:
        import aiofiles
        async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
            content = await f.read()
        return Document(content=content, source=str(path))

    async def _load_pdf(self, path: Path) -> Document:
        """Load PDF using PyPDF2 or pdfplumber."""
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return Document(content="\n\n".join(text_parts), source=str(path))
        except ImportError:
            logger.warning("pdfplumber not installed, reading PDF as text")
            return await self._load_text(path)

    async def _load_docx(self, path: Path) -> Document:
        """Load DOCX using python-docx."""
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(str(path))
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return Document(content=text, source=str(path))
        except ImportError:
            logger.warning("python-docx not installed, skipping DOCX")
            return Document(content="", source=str(path))

    async def _load_html(self, path: Path) -> Document:
        import aiofiles
        async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
            html = await f.read()
        # Simple HTML tag stripping
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return Document(content=text, source=str(path))
