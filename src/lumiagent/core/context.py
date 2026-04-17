"""Context builder - assembles complete LLM input from multiple sources."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from lumiagent.logging import get_logger
from lumiagent.models.llm import ChatMessage, ChatRole, ToolSchema
from lumiagent.models.message import UnifiedMessage
from lumiagent.models.tool import ToolResult

if TYPE_CHECKING:
    from lumiagent.core.memory import MemoryManager
    from lumiagent.rag.pipeline import RAGPipeline

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are LumiAgent, a helpful AI assistant.
You can use tools to help answer questions and complete tasks.
Think step by step. If you need more information, use the appropriate tool.
Always respond in the same language as the user's message."""


class AgentContext:
    """Mutable context that accumulates messages for LLM input."""

    def __init__(self) -> None:
        self._messages: list[ChatMessage] = []
        self._tool_schemas: list[ToolSchema] = []

    @property
    def messages(self) -> list[ChatMessage]:
        return self._messages

    @property
    def tool_schemas(self) -> list[ToolSchema]:
        return self._tool_schemas

    def set_tools(self, schemas: list[ToolSchema]) -> None:
        self._tool_schemas = schemas

    def add_system(self, content: str) -> None:
        self._messages.append(ChatMessage(role=ChatRole.SYSTEM, content=content))

    def add_user(self, content: str) -> None:
        self._messages.append(ChatMessage(role=ChatRole.USER, content=content))

    def add_assistant(self, content: str, tool_calls=None) -> None:
        self._messages.append(ChatMessage(
            role=ChatRole.ASSISTANT, content=content, tool_calls=tool_calls,
        ))

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append(ChatMessage(
            role=ChatRole.TOOL, content=content, tool_call_id=tool_call_id,
        ))

    def add_history(self, messages: list[ChatMessage]) -> None:
        self._messages.extend(messages)

    def to_messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def trim_to_budget(self, max_tokens: int, counter=None) -> None:
        """Trim older messages if context exceeds token budget (keep system + last N)."""
        if counter is None:
            return
        while len(self._messages) > 3:
            total = counter(self._messages)
            if total <= max_tokens:
                break
            # Remove the oldest non-system message
            for i, msg in enumerate(self._messages):
                if msg.role != ChatRole.SYSTEM:
                    self._messages.pop(i)
                    break


class ContextBuilder:
    """Builds complete AgentContext from message + memory + RAG."""

    def __init__(
        self,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        memory: Optional[MemoryManager] = None,
        rag: Optional[RAGPipeline] = None,
        max_context_tokens: int = 128000,
    ) -> None:
        self.system_prompt = system_prompt
        self.memory = memory
        self.rag = rag
        self.max_context_tokens = max_context_tokens

    async def build(self, message: UnifiedMessage, tool_schemas: list[ToolSchema] | None = None) -> AgentContext:
        ctx = AgentContext()

        # 1. System prompt
        ctx.add_system(self.system_prompt)

        # 2. Long-term memory
        if self.memory:
            long_term = await self.memory.recall_long_term(
                query=message.content.text or "",
                user_id=message.user_id,
            )
            if long_term:
                ctx.add_system(f"## Relevant Memories\n{long_term}")

        # 3. RAG retrieval
        if self.rag and message.content.text:
            rag_results = await self.rag.retrieve(message.content.text)
            if rag_results:
                formatted = "\n\n".join(
                    f"[Source: {r.source}]\n{r.content}" for r in rag_results
                )
                ctx.add_system(f"## Reference Knowledge\n{formatted}")

        # 4. Short-term memory (conversation history)
        if self.memory:
            history = await self.memory.recall_short_term(
                channel_id=message.channel_id,
            )
            ctx.add_history(history)

        # 5. Current user message
        ctx.add_user(message.content.text or "")

        # 6. Set available tools
        if tool_schemas:
            ctx.set_tools(tool_schemas)

        return ctx
