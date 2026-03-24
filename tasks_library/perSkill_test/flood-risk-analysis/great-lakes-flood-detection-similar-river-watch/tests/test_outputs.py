import json
import os


EXPECTED = [
    {
        "station_id": "04078500",
        "flood_days": 3,
        "flood_dates": ["2025-03-19", "2025-03-20", "2025-03-21"],
    },
    {
        "station_id": "04086000",
        "flood_days": 3,
        "flood_dates": ["2025-03-20", "2025-03-21", "2025-03-22"],
    },
    {
        "station_id": "04087000",
        "flood_days": 3,
        "flood_dates": ["2025-03-19", "2025-03-20", "2025-03-21"],
    },
    {
        "station_id": "05362000",
        "flood_days": 3,
        "flood_dates": ["2025-03-19", "2025-03-20", "2025-03-21"],
    },
    {
        "station_id": "04084500",
        "flood_days": 2,
        "flood_dates": ["2025-03-19", "2025-03-20"],
    },
]


def test_output_file_exists():
    assert os.path.exists("/root/output/river_watch_summary.json"), (
        "JSON output not found at /root/output/river_watch_summary.json"
    )


def test_output_matches_expected_payload():
    with open("/root/output/river_watch_summary.json", "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload == EXPECTED, f"Expected {EXPECTED}, got {payload}"


def test_non_window_and_non_roster_stations_are_excluded():
    with open("/root/output/river_watch_summary.json", "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    station_ids = [row["station_id"] for row in payload]
    assert "04090000" not in station_ids
    assert "05340500" not in station_ids
