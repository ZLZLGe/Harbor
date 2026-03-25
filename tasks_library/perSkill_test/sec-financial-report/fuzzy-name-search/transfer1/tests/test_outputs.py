import csv
from pathlib import Path


OUTPUT = Path("/root/fund_resolution_table.csv")
EXPECTED = Path("/tests/expected.csv")


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_output_exists():
    assert OUTPUT.exists(), "Missing /root/fund_resolution_table.csv"


def test_rows_match_expected():
    assert load_csv(OUTPUT) == load_csv(EXPECTED)
