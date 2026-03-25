from pathlib import Path


OUTPUT = Path("/root/watchlist_resolution.tsv")
EXPECTED = Path("/tests/expected.tsv")


def test_output_exists():
    assert OUTPUT.exists(), "Missing /root/watchlist_resolution.tsv"


def test_table_matches_expected():
    assert OUTPUT.read_text() == EXPECTED.read_text()
