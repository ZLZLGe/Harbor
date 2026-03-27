from packetlabels.labels import decode_label_frame, parse_label_row


def test_parse_label_row():
    row = parse_label_row("L-17,Z2,active")
    assert row["zone"] == "Z2"


def test_decode_label_frame():
    rows = decode_label_frame(b"L-17,Z2,active\nL-18,Z7,hold\n")
    assert len(rows) == 2
