import json
from pathlib import Path

from lumiagent.adapters.claude_code.transcript import enrich_transcript


def test_missing_transcript_returns_unsupported(tmp_path: Path) -> None:
    enrichment = enrich_transcript(tmp_path / "missing.jsonl", session_id="session_1")

    assert enrichment.status == "unsupported"
    assert enrichment.items == []
    assert enrichment.warnings


def test_jsonl_transcript_extracts_user_and_final_response(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "Fix the failing tests."}),
                json.dumps(
                    {"role": "assistant", "content": "I will inspect the failure and run pytest."}
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "content": "Fixed the issue and tests pass.",
                        "final": True,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    enrichment = enrich_transcript(transcript, session_id="session_1")

    assert enrichment.status == "success"
    assert [item.convention for item in enrichment.items] == [
        "user_prompt",
        "task_understanding",
        "final_response",
    ]
    assert enrichment.items[0].content_summary == "Fix the failing tests."


def test_summary_normalizes_whitespace_and_truncates_over_160_characters(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "long.jsonl"
    content = "word\n" + "x" * 170
    transcript.write_text(json.dumps({"role": "user", "content": content}), encoding="utf-8")

    enrichment = enrich_transcript(transcript, session_id="session_1")

    assert enrichment.items[0].content_summary == "word " + "x" * 152 + "..."
    assert len(enrichment.items[0].content_summary) == 160


def test_final_true_assistant_takes_precedence_over_last_assistant(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"role": "assistant", "content": "Planning."}),
                json.dumps({"role": "assistant", "content": "Final answer.", "final": True}),
                json.dumps({"role": "assistant", "content": "Follow-up note."}),
            ]
        ),
        encoding="utf-8",
    )

    enrichment = enrich_transcript(transcript, session_id="session_1")

    assert enrichment.items[-1].convention == "final_response"
    assert enrichment.items[-1].content == "Final answer."


def test_invalid_json_transcript_returns_unsupported(tmp_path: Path) -> None:
    transcript = tmp_path / "broken.jsonl"
    transcript.write_text("{not json", encoding="utf-8")

    enrichment = enrich_transcript(transcript, session_id="session_1")

    assert enrichment.status == "unsupported"
    assert enrichment.items == []
    assert enrichment.warnings


def test_nested_message_rows_are_supported_best_effort(tmp_path: Path) -> None:
    transcript = tmp_path / "nested.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "Fix the tests."},
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "I will inspect pytest."}],
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    enrichment = enrich_transcript(transcript, session_id="session_1")

    assert enrichment.status == "success"
    assert [item.convention for item in enrichment.items] == [
        "user_prompt",
        "task_understanding",
        "final_response",
    ]
    assert enrichment.items[1].content_summary == "I will inspect pytest."
