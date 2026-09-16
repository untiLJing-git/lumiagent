"""Evaluation metrics for Agent assessment."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MetricCategory(str, Enum):
    RESPONSE_QUALITY = "response_quality"
    TOOL_USAGE = "tool_usage"
    RAG_RETRIEVAL = "rag_retrieval"
    MEMORY = "memory"
    REASONING = "reasoning"
    SAFETY = "safety"
    LATENCY = "latency"


@dataclass
class Score:
    value: float  # 0.0 ~ 1.0
    category: MetricCategory
    metric_name: str
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalCase:
    id: str
    category: MetricCategory
    input: str
    expected_output: Optional[str] = None
    expected_tools: list[str] = field(default_factory=list)
    expected_docs: list[str] = field(default_factory=list)
    context: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    case_id: str
    scores: list[Score]
    actual_output: str = ""
    actual_tools: list[str] = field(default_factory=list)
    actual_trace: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class EvalReport:
    name: str
    total_cases: int
    results: list[EvalResult]
    summary: dict[str, float] = field(default_factory=dict)

    def compute_summary(self) -> None:
        """Compute average scores per category."""
        from collections import defaultdict
        category_scores: dict[str, list[float]] = defaultdict(list)

        for result in self.results:
            for score in result.scores:
                category_scores[score.category.value].append(score.value)

        self.summary = {
            cat: sum(vals) / len(vals) if vals else 0.0
            for cat, vals in category_scores.items()
        }

    @property
    def overall_score(self) -> float:
        if not self.summary:
            self.compute_summary()
        if not self.summary:
            return 0.0
        return sum(self.summary.values()) / len(self.summary)

    def to_markdown(self) -> str:
        self.compute_summary()
        lines = [
            f"# Evaluation Report: {self.name}",
            f"\n**Total Cases**: {self.total_cases}",
            f"**Overall Score**: {self.overall_score:.2%}",
            "\n## Category Scores\n",
            "| Category | Score |",
            "|----------|-------|",
        ]
        for cat, score in sorted(self.summary.items()):
            lines.append(f"| {cat} | {score:.2%} |")

        lines.append("\n## Detailed Results\n")
        for result in self.results:
            lines.append(f"### Case: {result.case_id}")
            if result.error:
                lines.append(f"**Error**: {result.error}")
            lines.append(f"**Latency**: {result.latency_ms:.0f}ms")
            for score in result.scores:
                lines.append(f"- {score.metric_name}: {score.value:.2%} - {score.details}")
            lines.append("")

        return "\n".join(lines)
