"""Memory system - short-term, long-term, proactive, and compression."""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from typing import Optional

from lumiagent.config import MemoryConfig
from lumiagent.logging import get_logger
from lumiagent.models.llm import ChatMessage, ChatRole
from lumiagent.models.memory import ConversationTurn, MemoryEntry, MemoryType
from lumiagent.models.message import AgentResponse, UnifiedMessage

logger = get_logger(__name__)


class ShortTermMemory:
    """In-memory conversation history per channel."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self._history: dict[str, list[ChatMessage]] = defaultdict(list)

    def add(self, channel_id: str, message: ChatMessage) -> None:
        history = self._history[channel_id]
        history.append(message)
        if len(history) > self.max_turns * 2:
            self._history[channel_id] = history[-(self.max_turns * 2):]

    def get(self, channel_id: str, limit: int | None = None) -> list[ChatMessage]:
        history = self._history[channel_id]
        if limit:
            return history[-limit:]
        return list(history)

    def clear(self, channel_id: str) -> None:
        self._history.pop(channel_id, None)


class LongTermMemory:
    """SQLite-backed long-term memory with vector search support."""

    def __init__(self, db_path: str = "./data/memory.db") -> None:
        self.db_path = db_path
        self._entries: list[MemoryEntry] = []  # In-memory fallback
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize SQLite database tables."""
        import aiosqlite
        from pathlib import Path

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    user_id TEXT,
                    channel_id TEXT,
                    importance REAL DEFAULT 0.5,
                    embedding BLOB,
                    metadata TEXT DEFAULT '{}',
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)
            """)
            await db.commit()

        self._initialized = True
        logger.info("Long-term memory initialized", db_path=self.db_path)

    async def store(self, entry: MemoryEntry) -> None:
        if not self._initialized:
            await self.initialize()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO memories
                   (id, memory_type, content, user_id, channel_id, importance,
                    embedding, metadata, created_at, accessed_at, access_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.id,
                    entry.memory_type.value,
                    entry.content,
                    entry.user_id,
                    entry.channel_id,
                    entry.importance,
                    json.dumps(entry.embedding) if entry.embedding else None,
                    json.dumps(entry.metadata),
                    entry.created_at,
                    entry.accessed_at,
                    entry.access_count,
                ),
            )
            await db.commit()

    async def search(
        self, query: str, user_id: str | None = None, top_k: int = 5
    ) -> list[MemoryEntry]:
        """Simple keyword search (vector search requires embedding integration)."""
        if not self._initialized:
            await self.initialize()

        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            sql = "SELECT * FROM memories WHERE content LIKE ?"
            params: list = [f"%{query}%"]
            if user_id:
                sql += " AND (user_id = ? OR user_id IS NULL)"
                params.append(user_id)
            sql += " ORDER BY importance DESC, accessed_at DESC LIMIT ?"
            params.append(top_k)

            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    MemoryEntry(
                        id=row["id"],
                        memory_type=MemoryType(row["memory_type"]),
                        content=row["content"],
                        user_id=row["user_id"],
                        channel_id=row["channel_id"],
                        importance=row["importance"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                        created_at=row["created_at"],
                        accessed_at=row["accessed_at"],
                        access_count=row["access_count"],
                    )
                    for row in rows
                ]


class MemoryCompressor:
    """Compresses conversation history into summaries."""

    def __init__(self, llm_chat_fn=None) -> None:
        self._llm_chat = llm_chat_fn

    async def compress(self, messages: list[ChatMessage]) -> str:
        """Compress a list of messages into a summary string."""
        if not messages:
            return ""

        if self._llm_chat:
            from lumiagent.models.llm import LLMRequest
            conversation_text = "\n".join(
                f"{m.role.value}: {m.content}" for m in messages if m.content
            )
            request = LLMRequest(
                messages=[
                    ChatMessage(
                        role=ChatRole.SYSTEM,
                        content="Summarize the following conversation concisely, preserving key facts, decisions, and user preferences.",
                    ),
                    ChatMessage(role=ChatRole.USER, content=conversation_text),
                ],
                max_tokens=512,
                temperature=0.3,
            )
            response = await self._llm_chat(request)
            return response.content

        # Fallback: simple truncation
        texts = [f"{m.role.value}: {m.content[:100]}" for m in messages[-10:]]
        return "Previous conversation summary:\n" + "\n".join(texts)


class MemoryManager:
    """Unified memory manager combining all memory types."""

    def __init__(self, config: MemoryConfig, llm_chat_fn=None) -> None:
        self.config = config
        self.short_term = ShortTermMemory(max_turns=config.short_term_max_turns)
        self.long_term = LongTermMemory(db_path=config.db_path)
        self.compressor = MemoryCompressor(llm_chat_fn=llm_chat_fn)
        self._importance_threshold = 0.6

    async def initialize(self) -> None:
        await self.long_term.initialize()

    async def recall_short_term(
        self, channel_id: str, limit: int | None = None
    ) -> list[ChatMessage]:
        return self.short_term.get(channel_id, limit=limit or self.config.short_term_max_turns)

    async def recall_long_term(
        self, query: str, user_id: str, top_k: int = 5
    ) -> str:
        entries = await self.long_term.search(query, user_id=user_id, top_k=top_k)
        if not entries:
            return ""
        return "\n".join(f"- {e.content}" for e in entries)

    async def proactive_recall(self, query: str, user_id: str) -> list[str]:
        """Proactively search for related memories based on current context."""
        entries = await self.long_term.search(query, user_id=user_id, top_k=3)
        return [e.content for e in entries]

    async def store_turn(
        self,
        channel_id: str,
        user_message: UnifiedMessage,
        agent_response: AgentResponse,
    ) -> None:
        # Store in short-term
        self.short_term.add(
            channel_id,
            ChatMessage(role=ChatRole.USER, content=user_message.content.text or ""),
        )
        self.short_term.add(
            channel_id,
            ChatMessage(role=ChatRole.ASSISTANT, content=agent_response.content.text or ""),
        )

        # Evaluate importance for long-term storage
        importance = await self._evaluate_importance(
            user_message.content.text or "", agent_response.content.text or ""
        )
        if importance >= self._importance_threshold:
            entry = MemoryEntry(
                id=uuid.uuid4().hex,
                memory_type=MemoryType.LONG_TERM,
                content=f"User ({user_message.user_name}): {user_message.content.text}\nAgent: {agent_response.content.text}",
                user_id=user_message.user_id,
                channel_id=channel_id,
                importance=importance,
            )
            await self.long_term.store(entry)
            logger.debug("Stored to long-term memory", importance=importance)

        # Check if compression is needed
        if self.config.compression_enabled:
            history = self.short_term.get(channel_id)
            if len(history) > self.config.compression_threshold_turns:
                await self._compress_history(channel_id)

    async def _evaluate_importance(self, user_msg: str, agent_msg: str) -> float:
        """Heuristic importance scoring (0.0~1.0)."""
        score = 0.3  # base
        combined = (user_msg + agent_msg).lower()

        # Boost for preference indicators
        preference_words = ["prefer", "like", "always", "never", "remember", "favorite",
                           "喜欢", "偏好", "记住", "总是", "从不"]
        if any(w in combined for w in preference_words):
            score += 0.3

        # Boost for factual content
        if any(c.isdigit() for c in combined):
            score += 0.1

        # Boost for longer, substantive exchanges
        if len(combined) > 200:
            score += 0.1

        # Boost for questions answered
        if "?" in user_msg or "？" in user_msg:
            score += 0.1

        return min(score, 1.0)

    async def _compress_history(self, channel_id: str) -> None:
        history = self.short_term.get(channel_id)
        if len(history) <= 10:
            return

        # Compress older messages, keep recent ones
        old_messages = history[:-10]
        recent_messages = history[-10:]

        summary = await self.compressor.compress(old_messages)

        # Store summary as long-term memory
        entry = MemoryEntry(
            id=uuid.uuid4().hex,
            memory_type=MemoryType.LONG_TERM,
            content=f"[Conversation Summary] {summary}",
            channel_id=channel_id,
            importance=0.5,
        )
        await self.long_term.store(entry)

        # Replace short-term with summary + recent
        self.short_term.clear(channel_id)
        self.short_term.add(
            channel_id,
            ChatMessage(role=ChatRole.SYSTEM, content=f"Previous conversation: {summary}"),
        )
        for msg in recent_messages:
            self.short_term.add(channel_id, msg)

        logger.info("Compressed conversation history", channel_id=channel_id)
