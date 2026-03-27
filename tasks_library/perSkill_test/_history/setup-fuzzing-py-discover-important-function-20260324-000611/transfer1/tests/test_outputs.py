import csv
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer1_regression_queue.csv")
EXPECTED_PATH = Path("/tests/expected.csv")


def csv_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_matches_expected():
    assert csv_rows(OUTPUT_PATH) == csv_rows(EXPECTED_PATH)
