from pathlib import Path

from lumiagent.adapters.coding.viewer import is_coding_trace
from lumiagent.tracing.serializer import from_json

CODING_FIXTURES = Path(__file__).parent / "fixtures"
CLAUDE_CODE_FIXTURES = Path(__file__).parents[1] / "claude_code" / "fixtures"


def test_coding_trace_fixtures_validate() -> None:
    for path in CODING_FIXTURES.glob("*.json"):
        run = from_json(path.read_text(encoding="utf-8"))

        assert is_coding_trace(run)
        assert run.root_spans


def test_sanitized_real_session_fixture_validates_without_local_paths() -> None:
    path = CLAUDE_CODE_FIXTURES / "real_session_sanitized_trace.json"
    raw = path.read_text(encoding="utf-8")
    run = from_json(raw)

    assert is_coding_trace(run)
    assert "D:/Projects" not in raw
    assert "D:\\Projects" not in raw
