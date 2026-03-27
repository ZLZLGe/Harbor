from mailroompkg.attachments import extract_message_parts, parse_attachment_manifest


def test_parse_attachment_manifest():
    items = parse_attachment_manifest('{"attachments": [{"name": "a.pdf"}, {"name": "b.csv"}]}')
    assert items[0]["name"] == "a.pdf"


def test_extract_message_parts():
    parts = extract_message_parts(b"hdr\n--PART--\nbody\n--PART--\nfooter")
    assert len(parts) == 3
