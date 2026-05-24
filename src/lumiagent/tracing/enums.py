"""Enums for LumiAgent trace models."""
from __future__ import annotations

from enum import Enum


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class SpanKind(str, Enum):
    AGENT = "agent"
    LLM = "llm"
    TOOL = "tool"
    RAG = "rag"
    MEMORY = "memory"
    EVALUATOR = "evaluator"
    FALLBACK = "fallback"
    ERROR = "error"
    CUSTOM = "custom"


class EventLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ArtifactKind(str, Enum):
    PROMPT = "prompt"
    COMPLETION = "completion"
    RETRIEVED_CHUNKS = "retrieved_chunks"
    TOOL_RESULT = "tool_result"
    CODE_DIFF = "code_diff"
    TEST_OUTPUT = "test_output"
    LOG = "log"
    CUSTOM = "custom"


class TargetType(str, Enum):
    RUN = "run"
    SPAN = "span"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
