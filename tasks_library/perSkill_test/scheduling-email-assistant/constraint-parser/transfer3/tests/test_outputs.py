import csv
from pathlib import Path


OUTPUT = Path("/root/transfer3_loading_constraints.csv")

EXPECTED_ROWS = [
    {
        "vendor_id": "vendor-77",
        "vendor_name": "Northline Produce",
        "arrival_dates": "2026-10-03|2026-10-04",
        "window_start": "06:00",
        "window_end": "09:00",
        "blocked_ranges": "2026-10-04 07:15-07:45",
        "unload_minutes": "50",
        "notes": "refrigerated bay required",
    },
    {
        "vendor_id": "vendor-81",
        "vendor_name": "Harbor Paper",
        "arrival_dates": "2026-11-12",
        "window_start": "13:00",
        "window_end": "15:30",
        "blocked_ranges": "2026-11-12 14:00-14:20",
        "unload_minutes": "35",
        "notes": "pallet jack on standby",
    },
    {
        "vendor_id": "vendor-90",
        "vendor_name": "Blue Mesa Foods",
        "arrival_dates": "2026-12-01|2026-12-02|2026-12-03",
        "window_start": "08:30",
        "window_end": "11:00",
        "blocked_ranges": "2026-12-02 09:15-09:45|2026-12-03 10:00-10:30",
        "unload_minutes": "70",
        "notes": "customs seal inspection first",
    },
]


def load_rows():
    with OUTPUT.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_output_exists():
    assert OUTPUT.exists(), "missing transfer3 output"


def test_output_matches_expected_rows():
    assert load_rows() == EXPECTED_ROWS


def test_vendor_count_and_combined_blocked_ranges():
    rows = load_rows()
    assert len(rows) == 3
    assert rows[2]["blocked_ranges"] == "2026-12-02 09:15-09:45|2026-12-03 10:00-10:30"
