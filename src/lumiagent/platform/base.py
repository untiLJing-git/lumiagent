"""Base platform adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from lumiagent.models.message import MessageContent, Platform, UnifiedMessage


MessageCallback = Callable[[UnifiedMessage], Awaitable[None]]


class PlatformAdapter(ABC):
    """Abstract base class for platform adapters."""

    def __init__(self) -> None:
        self._message_callbacks: list[MessageCallback] = []

    @property
    @abstractmethod
    def platform_name(self) -> Platform:
        """Return the platform identifier."""

    @abstractmethod
    async def start(self) -> None:
        """Start the adapter (connect, listen, etc.)."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the adapter and clean up resources."""

    @abstractmethod
    async def send_message(self, channel_id: str, content: MessageContent) -> None:
        """Send a message to the specified channel."""

    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback for incoming messages."""
        self._message_callbacks.append(callback)

    async def _dispatch(self, message: UnifiedMessage) -> None:
        """Dispatch a received message to all registered callbacks."""
        for callback in self._message_callbacks:
            await callback(message)
