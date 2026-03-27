import csv
from pathlib import Path


OUTPUT_PATH = Path("/root/transfer2_boundary_map.tsv")
EXPECTED_PATH = Path("/tests/expected.tsv")


def tsv_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_matches_expected():
    assert tsv_rows(OUTPUT_PATH) == tsv_rows(EXPECTED_PATH)
