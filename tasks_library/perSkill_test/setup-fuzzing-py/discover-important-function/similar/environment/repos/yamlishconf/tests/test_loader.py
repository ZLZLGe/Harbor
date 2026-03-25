from yamlishconf.loader import load_document


def test_load_document_rejects_invalid_line():
    try:
        load_document("bad-line")
    except ValueError as exc:
        assert "invalid line" in str(exc)
    else:
        raise AssertionError("expected ValueError")
