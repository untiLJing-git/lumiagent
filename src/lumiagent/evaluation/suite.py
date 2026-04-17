"""Evaluation suite - orchestrates running eval cases."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from lumiagent.config import EvalConfig
from lumiagent.evaluation.evaluators import (
    BaseEvaluator,
    LatencyEvaluator,
    RAGEvaluator,
    ResponseQualityEvaluator,
    SafetyEvaluator,
    ToolUsageEvaluator,
)
from lumiagent.evaluation.metrics import EvalCase, EvalReport, EvalResult, MetricCategory
from lumiagent.logging import get_logger

logger = get_logger(__name__)


class EvaluationSuite:
    """Runs evaluation cases against an Agent."""

    def __init__(self, config: EvalConfig, llm_chat_fn=None) -> None:
        self.config = config
        self._evaluators: list[BaseEvaluator] = [
            ResponseQualityEvaluator(llm_chat_fn=llm_chat_fn),
            ToolUsageEvaluator(),
            RAGEvaluator(),
            LatencyEvaluator(),
            SafetyEvaluator(),
        ]

    def add_evaluator(self, evaluator: BaseEvaluator) -> None:
        self._evaluators.append(evaluator)

    async def run(self, eval_set_name: str, agent_run_fn) -> EvalReport:
        """Run an evaluation set.
        
        Args:
            eval_set_name: Name of the eval set (matches a JSON file in eval_sets_dir).
            agent_run_fn: async function that takes a question string and returns
                         (output_text, trace_list, latency_ms).
        """
        cases = self._load_eval_set(eval_set_name)
        results: list[EvalResult] = []

        for case in cases:
            logger.info("Running eval case", case_id=case.id)
            result = await self._run_case(case, agent_run_fn)
            results.append(result)

        report = EvalReport(
            name=eval_set_name,
            total_cases=len(cases),
            results=results,
        )
        report.compute_summary()

        logger.info(
            "Evaluation complete",
            eval_set=eval_set_name,
            overall_score=report.overall_score,
        )
        return report

    async def _run_case(self, case: EvalCase, agent_run_fn) -> EvalResult:
        try:
            t0 = time.monotonic()
            output, trace, extra_kwargs = await agent_run_fn(case.input)
            latency_ms = (time.monotonic() - t0) * 1000

            scores = []
            for evaluator in self._evaluators:
                case_scores = await evaluator.evaluate(
                    case, output, trace,
                    latency_ms=latency_ms,
                    **extra_kwargs,
                )
                scores.extend(case_scores)

            return EvalResult(
                case_id=case.id,
                scores=scores,
                actual_output=output,
                actual_trace=trace,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.exception("Eval case failed", case_id=case.id)
            return EvalResult(
                case_id=case.id,
                scores=[],
                error=str(e),
            )

    def _load_eval_set(self, name: str) -> list[EvalCase]:
        """Load evaluation cases from a JSON file."""
        eval_dir = Path(self.config.eval_sets_dir)
        file_path = eval_dir / f"{name}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Eval set not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [
            EvalCase(
                id=item.get("id", f"{name}_{i}"),
                category=MetricCategory(item.get("category", "response_quality")),
                input=item["input"],
                expected_output=item.get("expected_output"),
                expected_tools=item.get("expected_tools", []),
                expected_docs=item.get("expected_docs", []),
                context=item.get("context", []),
                metadata=item.get("metadata", {}),
            )
            for i, item in enumerate(data.get("cases", data) if isinstance(data, dict) else data)
        ]

    def save_report(self, report: EvalReport, output_path: str | None = None) -> str:
        """Save evaluation report to file."""
        if output_path is None:
            output_path = f"./data/eval_reports/{report.name}_{int(time.time())}.md"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        content = report.to_markdown()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Report saved", path=output_path)
        return output_path
