import csv
import os
from datetime import date


OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/root/output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "pump_station_overflow_report.csv")


EXPECTED_ROWS = [
    {
        "pump_station_id": "PS-204",
        "overflow_risk_days": "4",
        "first_overflow_date": "2025-08-11",
    },
    {
        "pump_station_id": "PS-612",
        "overflow_risk_days": "2",
        "first_overflow_date": "2025-08-11",
    },
    {
        "pump_station_id": "PS-101",
        "overflow_risk_days": "3",
        "first_overflow_date": "2025-08-12",
    },
    {
        "pump_station_id": "PS-305",
        "overflow_risk_days": "1",
        "first_overflow_date": "2025-08-13",
    },
    {
        "pump_station_id": "PS-509",
        "overflow_risk_days": "2",
        "first_overflow_date": "2025-08-14",
    },
]


def load_rows():
    with open(OUTPUT_FILE, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def test_output_file_exists():
    assert os.path.exists(OUTPUT_FILE), (
        f"CSV output not found at {OUTPUT_FILE}"
    )


def test_output_rows_match_expected_report():
    fieldnames, rows = load_rows()
    assert fieldnames == [
        "pump_station_id",
        "overflow_risk_days",
        "first_overflow_date",
    ]
    assert rows == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS}, got {rows}"


def test_rows_are_sorted_and_non_reportable_stations_are_excluded():
    _, rows = load_rows()

    sort_keys = [
        (
            date.fromisoformat(row["first_overflow_date"]),
            -int(row["overflow_risk_days"]),
            row["pump_station_id"],
        )
        for row in rows
    ]
    assert sort_keys == sorted(sort_keys)

    station_ids = {row["pump_station_id"] for row in rows}
    assert "PS-407" not in station_ids
    assert "PS-999" not in station_ids
