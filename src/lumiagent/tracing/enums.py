"""Enums for LumiAgent trace models."""
from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class SpanKind(StrEnum):
    AGENT = "agent"
    LLM = "llm"
    TOOL = "tool"
    RAG = "rag"
    MEMORY = "memory"
    EVALUATOR = "evaluator"
    FALLBACK = "fallback"
    ERROR = "error"
    CUSTOM = "custom"


class EventLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ArtifactKind(StrEnum):
    PROMPT = "prompt"
    COMPLETION = "completion"
    RETRIEVED_CHUNKS = "retrieved_chunks"
    TOOL_RESULT = "tool_result"
    CODE_DIFF = "code_diff"
    TEST_OUTPUT = "test_output"
    LOG = "log"
    JSON = "json"
    CUSTOM = "custom"


class TargetType(StrEnum):
    RUN = "run"
    SPAN = "span"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
