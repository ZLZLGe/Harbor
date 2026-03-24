import json
import os


OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH", "/root/output/forecast_crest_risk.json"
)


def load_output():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), (
        "JSON file not found at /root/output/forecast_crest_risk.json"
    )


def test_output_matches_expected_payload():
    assert load_output() == {
        "issued_at": "2025-08-14T12:00:00Z",
        "window_end": "2025-08-16T12:00:00Z",
        "buckets": {
            "no_risk": [
                {
                    "station_id": "07010000",
                    "location_name": "Red Oak Landing",
                    "crest_valid_time": "2025-08-15T06:00:00Z",
                    "forecast_crest_ft": 9.8,
                    "reference_threshold": "action",
                    "threshold_ft": 10.0,
                    "margin_ft": -0.2,
                }
            ],
            "action": [
                {
                    "station_id": "07020000",
                    "location_name": "Blue Fork at Milltown",
                    "crest_valid_time": "2025-08-15T09:00:00Z",
                    "forecast_crest_ft": 8.0,
                    "reference_threshold": "action",
                    "threshold_ft": 8.0,
                    "margin_ft": 0.0,
                }
            ],
            "minor": [
                {
                    "station_id": "07030000",
                    "location_name": "Glenhaven at North Fork",
                    "crest_valid_time": "2025-08-15T12:00:00Z",
                    "forecast_crest_ft": 14.1,
                    "reference_threshold": "minor",
                    "threshold_ft": 13.0,
                    "margin_ft": 1.1,
                },
                {
                    "station_id": "07060000",
                    "location_name": "Stone Creek near Tucker",
                    "crest_valid_time": "2025-08-16T08:00:00Z",
                    "forecast_crest_ft": 10.8,
                    "reference_threshold": "minor",
                    "threshold_ft": 9.0,
                    "margin_ft": 1.8,
                },
            ],
            "moderate": [
                {
                    "station_id": "07040000",
                    "location_name": "Pine Ridge at Halstad",
                    "crest_valid_time": "2025-08-15T18:00:00Z",
                    "forecast_crest_ft": 20.0,
                    "reference_threshold": "moderate",
                    "threshold_ft": 18.5,
                    "margin_ft": 1.5,
                }
            ],
            "major": [
                {
                    "station_id": "07050000",
                    "location_name": "Eagle Bend at Riverport",
                    "crest_valid_time": "2025-08-15T20:00:00Z",
                    "forecast_crest_ft": 16.4,
                    "reference_threshold": "major",
                    "threshold_ft": 16.0,
                    "margin_ft": 0.4,
                }
            ],
        },
    }


def test_points_after_48_hours_are_ignored():
    payload = load_output()
    major_station_ids = {row["station_id"] for row in payload["buckets"]["major"]}
    moderate_station_ids = {row["station_id"] for row in payload["buckets"]["moderate"]}

    assert "07040000" in moderate_station_ids
    assert "07040000" not in major_station_ids

    minor_entry = next(
        row for row in payload["buckets"]["minor"] if row["station_id"] == "07060000"
    )
    assert minor_entry["crest_valid_time"] == "2025-08-16T08:00:00Z"


def test_non_watchlist_station_is_excluded():
    payload = load_output()
    included_station_ids = {
        row["station_id"]
        for bucket_rows in payload["buckets"].values()
        for row in bucket_rows
    }
    assert "07990000" not in included_station_ids
