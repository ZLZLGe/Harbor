from ledgerparse.parser import decode_ledger_csv, parse_invoice_text


def test_parse_invoice_text():
    rows = parse_invoice_text("north|INV-1|17.5\nsouth|INV-2|22.0")
    assert rows[0]["vendor"] == "north"
    assert rows[1]["invoice_id"] == "INV-2"


def test_decode_ledger_csv():
    rows = decode_ledger_csv("vendor,total\nnorth,17.5\nsouth,22.0\n")
    assert rows[1]["vendor"] == "south"
