"""Unified message models for cross-platform communication."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    CARD = "card"
    SYSTEM = "system"


class Platform(str, Enum):
    CMD = "cmd"
    WEB = "web"
    WECHAT = "wechat"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"


class ImageData(BaseModel):
    url: Optional[str] = None
    base64: Optional[str] = None
    mime_type: str = "image/png"
    width: Optional[int] = None
    height: Optional[int] = None


class FileData(BaseModel):
    url: Optional[str] = None
    name: str = ""
    mime_type: str = "application/octet-stream"
    size: Optional[int] = None


class AudioData(BaseModel):
    url: Optional[str] = None
    base64: Optional[str] = None
    duration_ms: Optional[int] = None
    mime_type: str = "audio/wav"


class CardData(BaseModel):
    title: str = ""
    content: str = ""
    actions: list[dict[str, Any]] = Field(default_factory=list)
    raw: Optional[dict[str, Any]] = None


class MessageContent(BaseModel):
    text: Optional[str] = None
    images: list[ImageData] = Field(default_factory=list)
    files: list[FileData] = Field(default_factory=list)
    audio: Optional[AudioData] = None
    card: Optional[CardData] = None

    @classmethod
    def from_text(cls, text: str) -> MessageContent:
        return cls(text=text)


class UnifiedMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    platform: Platform
    channel_id: str
    user_id: str
    user_name: str = ""
    content: MessageContent
    message_type: MessageType = MessageType.TEXT
    reply_to: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    @classmethod
    def text(
        cls,
        text: str,
        *,
        platform: Platform,
        channel_id: str,
        user_id: str,
        user_name: str = "",
    ) -> UnifiedMessage:
        return cls(
            platform=platform,
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
            content=MessageContent.from_text(text),
        )


class AgentResponse(BaseModel):
    content: MessageContent
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    error: bool = False

    @classmethod
    def text(cls, text: str) -> AgentResponse:
        return cls(content=MessageContent.from_text(text))
