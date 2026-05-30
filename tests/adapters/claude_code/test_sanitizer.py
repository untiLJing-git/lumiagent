from lumiagent.adapters.claude_code.sanitizer import sanitize_payload, sanitize_text


def test_sanitize_text_redacts_secret_like_values() -> None:
    text = "OPENAI_API_KEY=sk-test123 password: hunter2 bearer abc.def.ghi"

    sanitized = sanitize_text(text)

    assert "sk-test123" not in sanitized
    assert "hunter2" not in sanitized
    assert "abc.def.ghi" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_payload_redacts_nested_secret_fields() -> None:
    payload = {
        "tool_input": {
            "api_key": "sk-test123",
            "nested": {"authorization": "Bearer abc.def.ghi"},
        },
        "stdout": "token=secret-token",
    }

    sanitized = sanitize_payload(payload)

    assert sanitized["tool_input"]["api_key"] == "[REDACTED]"
    assert sanitized["tool_input"]["nested"]["authorization"] == "[REDACTED]"
    assert sanitized["stdout"] == "token=[REDACTED]"
