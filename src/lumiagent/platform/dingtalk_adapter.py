"""DingTalk platform adapter stub."""
from __future__ import annotations

from lumiagent.logging import get_logger
from lumiagent.models.message import MessageContent, Platform
from lumiagent.platform.base import PlatformAdapter

logger = get_logger(__name__)


class DingTalkAdapter(PlatformAdapter):
    """DingTalk adapter using dingtalk-stream SDK.
    
    Requires: pip install dingtalk-stream
    Config: DINGTALK_CLIENT_ID, DINGTALK_CLIENT_SECRET
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def platform_name(self) -> Platform:
        return Platform.DINGTALK

    async def start(self) -> None:
        # TODO: Initialize DingTalk stream client
        #   import dingtalk_stream
        #   credential = dingtalk_stream.Credential(self.client_id, self.client_secret)
        #   client = dingtalk_stream.DingTalkStreamClient(credential)
        #   client.register_callback_handler(...)
        logger.info("DingTalk adapter started (stub)")

    async def stop(self) -> None:
        logger.info("DingTalk adapter stopped")

    async def send_message(self, channel_id: str, content: MessageContent) -> None:
        # TODO: Use DingTalk API to send message
        logger.info("DingTalk send_message (stub)", channel_id=channel_id)
