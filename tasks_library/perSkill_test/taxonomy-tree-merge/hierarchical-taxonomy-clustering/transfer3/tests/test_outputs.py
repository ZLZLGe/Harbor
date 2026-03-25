import csv
import os
from pathlib import Path


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))
REFERENCE_DIR = Path(os.getenv("REFERENCE_DIR", "/root/reference"))


def load_tsv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_output_files_exist():
    assert (OUTPUT_DIR / "transfer3_search_routes.tsv").exists()
    assert (OUTPUT_DIR / "transfer3_route_catalog.md").exists()


def test_route_table_matches_reference():
    actual = load_tsv(OUTPUT_DIR / "transfer3_search_routes.tsv")
    expected = load_tsv(REFERENCE_DIR / "expected_routes.tsv")
    assert actual == expected


def test_markdown_catalog_matches_reference():
    actual = (OUTPUT_DIR / "transfer3_route_catalog.md").read_text(encoding="utf-8")
    expected = (REFERENCE_DIR / "expected_catalog.md").read_text(encoding="utf-8")
    assert actual == expected


def test_all_sources_have_five_rows():
    actual = load_tsv(OUTPUT_DIR / "transfer3_search_routes.tsv")
    counts = {}
    for row in actual:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    assert counts == {"planner_a": 5, "planner_b": 5, "planner_c": 5}


def test_route_slug_count_is_five():
    actual = load_tsv(OUTPUT_DIR / "transfer3_search_routes.tsv")
    slugs = sorted({row["route_slug"] for row in actual})
    assert slugs == [
        "drawer-dividers",
        "laundry-hampers",
        "over-door-hooks",
        "shoe-racks",
        "storage-bins",
    ]
