"""Command-line interface adapter using Rich for rendering."""
from __future__ import annotations

import asyncio
import sys

from lumiagent.logging import get_logger
from lumiagent.models.message import (
    MessageContent,
    MessageType,
    Platform,
    UnifiedMessage,
)
from lumiagent.platform.base import PlatformAdapter

logger = get_logger(__name__)

USER_ID = "cmd_user"
CHANNEL_ID = "cmd_session"


class CMDAdapter(PlatformAdapter):
    """Interactive command-line adapter."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._input_task: asyncio.Task | None = None

    @property
    def platform_name(self) -> Platform:
        return Platform.CMD

    async def start(self) -> None:
        self._running = True
        self._input_task = asyncio.create_task(self._read_loop())
        logger.info("CMD adapter started")

    async def stop(self) -> None:
        self._running = False
        if self._input_task:
            self._input_task.cancel()
        logger.info("CMD adapter stopped")

    async def send_message(self, channel_id: str, content: MessageContent) -> None:
        if content.text:
            print(f"\n🤖 Agent: {content.text}\n")
        if content.images:
            for img in content.images:
                print(f"  [Image: {img.url or 'base64 data'}]")
        if content.files:
            for f in content.files:
                print(f"  [File: {f.name}]")

    async def _read_loop(self) -> None:
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                line = await loop.run_in_executor(None, self._blocking_input)
                if line is None:
                    break
                line = line.strip()
                if not line:
                    continue
                if line.lower() in ("exit", "quit", "/quit"):
                    self._running = False
                    break

                message = UnifiedMessage.text(
                    text=line,
                    platform=Platform.CMD,
                    channel_id=CHANNEL_ID,
                    user_id=USER_ID,
                    user_name="User",
                )
                await self._dispatch(message)
            except (EOFError, KeyboardInterrupt):
                self._running = False
                break
            except Exception:
                logger.exception("Error in CMD input loop")

    @staticmethod
    def _blocking_input() -> str | None:
        try:
            return input("👤 You: ")
        except EOFError:
            return None
