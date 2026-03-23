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
    assert (OUTPUT_DIR / "transfer1_grocery_rollup.csv").exists()
    assert (OUTPUT_DIR / "transfer1_taxonomy_nodes.json").exists()


def test_rollup_matches_reference():
    actual = load_csv(OUTPUT_DIR / "transfer1_grocery_rollup.csv")
    expected = load_csv(REFERENCE_DIR / "expected_rollup.csv")
    assert actual == expected


def test_node_list_matches_reference():
    actual = json.loads((OUTPUT_DIR / "transfer1_taxonomy_nodes.json").read_text(encoding="utf-8"))
    expected = json.loads((REFERENCE_DIR / "expected_nodes.json").read_text(encoding="utf-8"))
    assert actual == expected


def test_every_source_has_all_rows():
    actual = load_csv(OUTPUT_DIR / "transfer1_grocery_rollup.csv")
    counts = {}
    for row in actual:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    assert counts == {"grocer_a": 5, "grocer_b": 5, "grocer_c": 5}


def test_unified_departments_are_expected():
    actual = load_csv(OUTPUT_DIR / "transfer1_grocery_rollup.csv")
    departments = sorted({row["unified_department"] for row in actual})
    assert departments == ["beverages", "pantry", "refrigerated", "snacks"]
