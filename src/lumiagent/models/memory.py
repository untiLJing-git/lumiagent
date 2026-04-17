"""Memory system models."""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    PROACTIVE = "proactive"


class MemoryEntry(BaseModel):
    id: str
    memory_type: MemoryType
    content: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    importance: float = 0.5
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0


class ConversationTurn(BaseModel):
    role: str
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)
