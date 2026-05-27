from lumiagent.tracing import TraceWriter


def test_trace_writer_protocol_is_public() -> None:
    assert TraceWriter.__name__ == "TraceWriter"
