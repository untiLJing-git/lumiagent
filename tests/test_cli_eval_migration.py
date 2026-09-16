import importlib
import sys

from typer.testing import CliRunner

import lumiagent.cli as cli


def test_eval_only_explains_migration_without_initializing_agent(monkeypatch) -> None:
    called = []

    async def forbidden(*args):
        called.append(args)
        raise AssertionError("Reserved eval must not initialize the legacy Agent")

    monkeypatch.setattr(cli, "_run_eval", forbidden, raising=False)
    monkeypatch.setattr(cli, "_run_legacy_eval", forbidden, raising=False)
    before = set(sys.modules)
    result = CliRunner().invoke(cli.app, ["eval", "sample_eval"])
    assert result.exit_code == 2
    assert "legacy-eval" in result.output
    assert "not implemented" in result.output
    assert called == []
    assert not any(
        name.startswith(("lumiagent.agent", "lumiagent.rag")) for name in set(sys.modules) - before
    )


def test_legacy_help_does_not_run_agent() -> None:
    result = CliRunner().invoke(cli.app, ["legacy-eval", "--help"])
    assert result.exit_code == 0
    assert "Legacy" in result.output
    assert "Phase 4" in result.output


def test_legacy_cli_is_wired_to_legacy_runner(monkeypatch) -> None:
    calls = []

    async def run(name, output):
        calls.append((name, output))

    monkeypatch.setattr(cli, "_run_legacy_eval", run, raising=False)
    result = CliRunner().invoke(cli.app, ["legacy-eval", "sample_eval", "--output", "out.md"])
    assert result.exit_code == 0
    assert calls == [("sample_eval", "out.md")]
    assert "deprecated" in result.output


def test_new_namespace_does_not_export_legacy_suite() -> None:
    evaluation = importlib.import_module("lumiagent.evaluation")
    assert not hasattr(evaluation, "EvaluationSuite")


def test_legacy_modules_import_from_their_new_namespace() -> None:
    module = importlib.import_module("lumiagent.legacy_eval.suite")
    assert module.EvaluationSuite.__module__ == "lumiagent.legacy_eval.suite"
    metrics = importlib.import_module("lumiagent.legacy_eval.metrics")
    assert module.EvalCase is metrics.EvalCase
