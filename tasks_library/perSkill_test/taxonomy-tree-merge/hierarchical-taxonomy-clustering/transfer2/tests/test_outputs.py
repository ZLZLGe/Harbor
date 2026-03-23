import csv
import json
import os
from pathlib import Path


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))
REFERENCE_DIR = Path(os.getenv("REFERENCE_DIR", "/root/reference"))


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_output_files_exist():
    assert (OUTPUT_DIR / "transfer2_bundle_assignments.json").exists()
    assert (OUTPUT_DIR / "transfer2_cluster_summary.csv").exists()


def test_assignment_json_matches_reference():
    actual = json.loads((OUTPUT_DIR / "transfer2_bundle_assignments.json").read_text(encoding="utf-8"))
    expected = json.loads((REFERENCE_DIR / "expected_assignments.json").read_text(encoding="utf-8"))
    assert actual == expected


def test_cluster_summary_matches_reference():
    actual = load_csv(OUTPUT_DIR / "transfer2_cluster_summary.csv")
    expected = load_csv(REFERENCE_DIR / "expected_summary.csv")
    assert actual == expected


def test_all_sources_contribute_five_rows():
    actual = json.loads((OUTPUT_DIR / "transfer2_bundle_assignments.json").read_text(encoding="utf-8"))
    counts = {}
    for row in actual:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    assert counts == {"supplier_one": 5, "supplier_three": 5, "supplier_two": 5}


def test_cluster_count_is_five():
    actual = load_csv(OUTPUT_DIR / "transfer2_cluster_summary.csv")
    assert len(actual) == 5
