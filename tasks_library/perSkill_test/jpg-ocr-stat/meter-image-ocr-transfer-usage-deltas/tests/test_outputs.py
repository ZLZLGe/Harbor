import json
import os
from decimal import Decimal
from pathlib import Path


OUTPUT_FILE = Path("/app/workspace/meter_consumption.json")
EXPECTED_READINGS = [
    {
        "filename": "yard_cam_11.png",
        "date": "2025-01-17",
        "reading": "1842.7",
        "delta_from_previous": None,
    },
    {
        "filename": "yard_cam_14.png",
        "date": "2025-02-04",
        "reading": "1855.9",
        "delta_from_previous": "13.2",
    },
    {
        "filename": "yard_cam_03.png",
        "date": "2025-02-19",
        "reading": "1870.4",
        "delta_from_previous": "14.5",
    },
    {
        "filename": "yard_cam_02.png",
        "date": "2025-03-07",
        "reading": "1889.1",
        "delta_from_previous": "18.7",
    },
    {
        "filename": "yard_cam_07.png",
        "date": "2025-03-26",
        "reading": "1901.6",
        "delta_from_previous": "12.5",
    },
]
EXPECTED_TOTAL = "58.9"


def test_output_file_exists():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"


def test_output_schema_and_values():
    payload = json.loads(OUTPUT_FILE.read_text())

    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"readings", "total_consumption"}
    assert payload["readings"] == EXPECTED_READINGS
    assert payload["total_consumption"] == EXPECTED_TOTAL


def test_dates_are_sorted_and_deltas_match_readings():
    payload = json.loads(OUTPUT_FILE.read_text())
    readings = payload["readings"]

    dates = [item["date"] for item in readings]
    assert dates == sorted(dates), f"readings are not sorted by date: {dates}"

    decimal_readings = [Decimal(item["reading"]) for item in readings]
    assert readings[0]["delta_from_previous"] is None

    for index in range(1, len(readings)):
        expected_delta = f"{(decimal_readings[index] - decimal_readings[index - 1]):.1f}"
        assert readings[index]["delta_from_previous"] == expected_delta

    total = f"{(decimal_readings[-1] - decimal_readings[0]):.1f}"
    assert payload["total_consumption"] == total
