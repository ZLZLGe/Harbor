import csv
import os
from pathlib import Path


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))
REFERENCE_DIR = Path(os.getenv("REFERENCE_DIR", "/root/reference"))


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_output_files_exist():
    assert (OUTPUT_DIR / "similar_outdoor_taxonomy_full.csv").exists()
    assert (OUTPUT_DIR / "similar_outdoor_taxonomy_hierarchy.csv").exists()


def test_full_mapping_matches_reference():
    actual = load_csv(OUTPUT_DIR / "similar_outdoor_taxonomy_full.csv")
    expected = load_csv(REFERENCE_DIR / "expected_full.csv")
    assert actual == expected


def test_hierarchy_matches_reference():
    actual = load_csv(OUTPUT_DIR / "similar_outdoor_taxonomy_hierarchy.csv")
    expected = load_csv(REFERENCE_DIR / "expected_hierarchy.csv")
    assert actual == expected


def test_every_source_record_is_preserved():
    actual = load_csv(OUTPUT_DIR / "similar_outdoor_taxonomy_full.csv")
    counts = {}
    for row in actual:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    assert counts == {"alpha": 6, "bravo": 6, "charlie": 6}


def test_unified_leaf_set_is_complete():
    actual = load_csv(OUTPUT_DIR / "similar_outdoor_taxonomy_full.csv")
    leaves = sorted({row["unified_level_5"] for row in actual})
    assert leaves == ["chair", "cooler", "lantern", "sleeping bag", "stove", "tent"]
