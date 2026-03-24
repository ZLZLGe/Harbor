import csv
import os


OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/root/output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "underpass_closure_days.csv")


EXPECTED_ROWS = [
    {
        "underpass_id": "UP-512",
        "blocked_days": "4",
        "worst_closure_category": "traffic_control",
    },
    {
        "underpass_id": "UP-101",
        "blocked_days": "3",
        "worst_closure_category": "full_closure",
    },
    {
        "underpass_id": "UP-205",
        "blocked_days": "3",
        "worst_closure_category": "full_closure",
    },
    {
        "underpass_id": "UP-318",
        "blocked_days": "3",
        "worst_closure_category": "full_closure",
    },
    {
        "underpass_id": "UP-404",
        "blocked_days": "3",
        "worst_closure_category": "full_closure",
    },
]


def load_csv():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def test_output_file_exists():
    assert os.path.exists(OUTPUT_FILE), (
        f"CSV output not found at {OUTPUT_FILE}"
    )


def test_output_rows_and_sort_order():
    fieldnames, rows = load_csv()
    assert fieldnames == [
        "underpass_id",
        "blocked_days",
        "worst_closure_category",
    ]
    assert rows == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS}, got {rows}"


def test_non_blocked_and_unconfigured_underpasses_are_excluded():
    _, rows = load_csv()
    underpass_ids = {row["underpass_id"] for row in rows}

    assert "UP-620" not in underpass_ids
    assert "UP-730" not in underpass_ids
    assert "UP-777" not in underpass_ids
