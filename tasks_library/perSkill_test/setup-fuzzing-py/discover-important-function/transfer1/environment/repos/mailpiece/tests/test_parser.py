from mailpiece.parser import parse_message


def test_parse_message_requires_separator():
    try:
        parse_message(b"subject: hi")
    except ValueError as exc:
        assert "separator" in str(exc)
    else:
        raise AssertionError("expected ValueError")
