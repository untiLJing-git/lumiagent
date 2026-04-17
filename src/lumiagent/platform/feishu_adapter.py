"""Feishu (Lark) platform adapter stub."""
from __future__ import annotations

from lumiagent.logging import get_logger
from lumiagent.models.message import MessageContent, Platform
from lumiagent.platform.base import PlatformAdapter

logger = get_logger(__name__)


class FeishuAdapter(PlatformAdapter):
    """Feishu adapter using lark-oapi SDK.
    
    Requires: pip install lark-oapi
    Config: FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_VERIFICATION_TOKEN
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        verification_token: str = "",
        encrypt_key: str = "",
    ) -> None:
        super().__init__()
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key

    @property
    def platform_name(self) -> Platform:
        return Platform.FEISHU

    async def start(self) -> None:
        # TODO: Initialize lark-oapi client, register event handlers
        #   from lark_oapi import Client, Config
        #   self.client = Client.builder().app_id(self.app_id)...build()
        #   Register im.message.receive_v1 event
        logger.info("Feishu adapter started (stub)")

    async def stop(self) -> None:
        logger.info("Feishu adapter stopped")

    async def send_message(self, channel_id: str, content: MessageContent) -> None:
        # TODO: Use lark-oapi to send message
        #   from lark_oapi.api.im.v1 import CreateMessageRequest
        #   Build request with chat_id=channel_id, msg_type="text", content=...
        logger.info("Feishu send_message (stub)", channel_id=channel_id)
