"""Agent assembly - wires all components together."""
from __future__ import annotations

from lumiagent.config import Settings
from lumiagent.core.context import ContextBuilder
from lumiagent.core.engine import ReActEngine
from lumiagent.core.memory import MemoryManager
from lumiagent.llm.router import LLMRouter
from lumiagent.logging import get_logger
from lumiagent.models.message import AgentResponse, UnifiedMessage
from lumiagent.platform.manager import PlatformManager
from lumiagent.tools.registry import ToolRegistry
from lumiagent.tools.mcp_bridge import MCPBridge
from lumiagent.models.tool import MCPServerConfig

logger = get_logger(__name__)


class Agent:
    """Top-level Agent that wires all components."""

    def __init__(
        self,
        settings: Settings,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        memory: MemoryManager,
        engine: ReActEngine,
        platform_manager: PlatformManager,
        mcp_bridge: MCPBridge | None = None,
    ) -> None:
        self.settings = settings
        self.llm = llm_router
        self.tools = tool_registry
        self.memory = memory
        self.engine = engine
        self.platforms = platform_manager
        self.mcp_bridge = mcp_bridge

    async def start(self, platforms: list[str] | None = None) -> None:
        """Start the Agent with specified platforms."""
        await self.memory.initialize()

        # Connect MCP servers
        if self.mcp_bridge and self.settings.tools.mcp_servers:
            for server_cfg in self.settings.tools.mcp_servers:
                config = MCPServerConfig(**server_cfg)
                await self.mcp_bridge.connect(config)

        # Register message handler
        self.platforms.on_message(self._handle_message)

        # Start platforms
        await self.platforms.start_all()

        logger.info("Agent started")

        # Keep running
        import asyncio
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            await self.stop()

    async def stop(self) -> None:
        await self.platforms.stop_all()
        logger.info("Agent stopped")

    async def _handle_message(self, message: UnifiedMessage) -> None:
        """Handle incoming message from any platform."""
        logger.info(
            "Message received",
            platform=message.platform.value,
            user=message.user_name,
            text=(message.content.text or "")[:100],
        )

        try:
            response = await self.engine.run(message)
        except Exception:
            logger.exception("Error processing message")
            response = AgentResponse.text("Sorry, something went wrong. Please try again.")

        # Send response back through the platform
        await self.platforms.send_to_platform(
            platform=message.platform,
            channel_id=message.channel_id,
            content=response.content,
        )

        # Handle REST API response future
        if "_response_future" in message.metadata:
            future = message.metadata["_response_future"]
            if not future.done():
                future.set_result(response.content.text or "")


async def create_agent(settings: Settings) -> Agent:
    """Factory function to create a fully wired Agent."""
    # LLM Router
    llm_router = LLMRouter(settings)

    # Tool Registry
    tool_registry = ToolRegistry()
    tool_registry.register_defaults()

    # MCP Bridge
    mcp_bridge = MCPBridge(tool_registry)

    # Memory Manager
    memory = MemoryManager(
        config=settings.memory,
        llm_chat_fn=llm_router.primary.chat,
    )

    # RAG Pipeline (if enabled)
    rag = None
    if settings.rag.enabled and settings.openai_api_key:
        from lumiagent.rag.embedder import OpenAIEmbedder
        from lumiagent.rag.pipeline import RAGPipeline
        embedder = OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )
        rag = RAGPipeline(config=settings.rag, embedder=embedder)

    # Context Builder
    context_builder = ContextBuilder(
        memory=memory,
        rag=rag,
        max_context_tokens=settings.max_context_tokens,
    )

    # ReAct Engine
    engine = ReActEngine(
        settings=settings,
        llm_router=llm_router,
        tool_registry=tool_registry,
        memory=memory,
        context_builder=context_builder,
    )

    # Platform Manager
    platform_manager = PlatformManager(settings)

    return Agent(
        settings=settings,
        llm_router=llm_router,
        tool_registry=tool_registry,
        memory=memory,
        engine=engine,
        platform_manager=platform_manager,
        mcp_bridge=mcp_bridge,
    )
