"""Platform manager - orchestrates all platform adapters."""
from __future__ import annotations

from lumiagent.config import Settings
from lumiagent.logging import get_logger
from lumiagent.models.message import Platform, UnifiedMessage
from lumiagent.platform.base import MessageCallback, PlatformAdapter
from lumiagent.platform.cmd_adapter import CMDAdapter
from lumiagent.platform.web_adapter import WebAdapter

logger = get_logger(__name__)


class PlatformManager:
    """Manages lifecycle of all platform adapters."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._adapters: dict[Platform, PlatformAdapter] = {}
        self._message_callback: MessageCallback | None = None

    def register_adapter(self, adapter: PlatformAdapter) -> None:
        self._adapters[adapter.platform_name] = adapter
        if self._message_callback:
            adapter.on_message(self._message_callback)
        logger.info("Platform adapter registered", platform=adapter.platform_name.value)

    def on_message(self, callback: MessageCallback) -> None:
        self._message_callback = callback
        for adapter in self._adapters.values():
            adapter.on_message(callback)

    async def start_all(self) -> None:
        await self._auto_register()
        for platform, adapter in self._adapters.items():
            try:
                await adapter.start()
                logger.info("Platform started", platform=platform.value)
            except Exception:
                logger.exception("Failed to start platform", platform=platform.value)

    async def stop_all(self) -> None:
        for platform, adapter in self._adapters.items():
            try:
                await adapter.stop()
            except Exception:
                logger.exception("Failed to stop platform", platform=platform.value)

    async def send_to_platform(
        self, platform: Platform, channel_id: str, content: "MessageContent"
    ) -> None:
        adapter = self._adapters.get(platform)
        if not adapter:
            logger.error("No adapter for platform", platform=platform.value)
            return
        await adapter.send_message(channel_id, content)

    async def _auto_register(self) -> None:
        cfg = self.settings.platform

        if cfg.cmd_enabled:
            self.register_adapter(CMDAdapter())

        if cfg.web_enabled:
            self.register_adapter(WebAdapter(host=cfg.web_host, port=cfg.web_port))

        if cfg.feishu_enabled and cfg.feishu_app_id:
            from lumiagent.platform.feishu_adapter import FeishuAdapter
            self.register_adapter(FeishuAdapter(
                app_id=cfg.feishu_app_id,
                app_secret=cfg.feishu_app_secret,
                verification_token=cfg.feishu_verification_token,
                encrypt_key=cfg.feishu_encrypt_key,
            ))

        if cfg.dingtalk_enabled and cfg.dingtalk_client_id:
            from lumiagent.platform.dingtalk_adapter import DingTalkAdapter
            self.register_adapter(DingTalkAdapter(
                client_id=cfg.dingtalk_client_id,
                client_secret=cfg.dingtalk_client_secret,
            ))

        if cfg.wechat_enabled and cfg.wechat_corp_id:
            from lumiagent.platform.wechat_adapter import WeChatAdapter
            self.register_adapter(WeChatAdapter(
                corp_id=cfg.wechat_corp_id,
                corp_secret=cfg.wechat_corp_secret,
                agent_id=cfg.wechat_agent_id,
                token=cfg.wechat_token,
                aes_key=cfg.wechat_aes_key,
            ))
