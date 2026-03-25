from recordframe.parser import parse_record_stream


def test_parse_record_stream_rejects_missing_separator():
    payload = b"alpha\n"
    blob = len(payload).to_bytes(2, "big") + payload
    try:
        parse_record_stream(blob)
    except ValueError as exc:
        assert "separator" in str(exc)
    else:
        raise AssertionError("expected ValueError")
