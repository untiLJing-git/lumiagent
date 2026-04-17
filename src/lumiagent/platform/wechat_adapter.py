"""WeChat (Enterprise WeChat) platform adapter stub."""
from __future__ import annotations

from lumiagent.logging import get_logger
from lumiagent.models.message import MessageContent, Platform
from lumiagent.platform.base import PlatformAdapter

logger = get_logger(__name__)


class WeChatAdapter(PlatformAdapter):
    """WeChat / Enterprise WeChat adapter.
    
    Supports two modes:
    - Enterprise WeChat API (企业微信)
    - WeChatFerry bridge (个人微信, requires wechatferry)
    
    Config: WECHAT_CORP_ID, WECHAT_CORP_SECRET, WECHAT_AGENT_ID
    """

    def __init__(
        self,
        corp_id: str,
        corp_secret: str,
        agent_id: str = "",
        token: str = "",
        aes_key: str = "",
    ) -> None:
        super().__init__()
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.token = token
        self.aes_key = aes_key

    @property
    def platform_name(self) -> Platform:
        return Platform.WECHAT

    async def start(self) -> None:
        # TODO: Initialize WeChat API client, set up webhook receiver
        logger.info("WeChat adapter started (stub)")

    async def stop(self) -> None:
        logger.info("WeChat adapter stopped")

    async def send_message(self, channel_id: str, content: MessageContent) -> None:
        # TODO: Use WeChat API to send message
        logger.info("WeChat send_message (stub)", channel_id=channel_id)
