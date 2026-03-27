from windowcalc.schedule import load_window_table, parse_window_row


def test_parse_window_row():
    row = parse_window_row("W-7|08:00|11:00")
    assert row["end"] == "11:00"


def test_load_window_table():
    rows = load_window_table("window_id,hours\nW-7,3\n")
    assert rows[0]["hours"] == "3"
