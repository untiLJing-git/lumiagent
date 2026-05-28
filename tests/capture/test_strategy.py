from lumiagent.capture import CaptureStrategy


def test_capture_strategy_protocol_is_public() -> None:
    assert CaptureStrategy.__name__ == "CaptureStrategy"
