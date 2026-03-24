import json
import os


OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH", "/root/output/river_access_advisories.json"
)


def load_output():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), (
        "JSON file not found at /root/output/river_access_advisories.json"
    )


def test_output_schema_and_count():
    payload = load_output()
    assert list(payload.keys()) == ["snapshot_time", "advisory_count", "advisories"]
    assert payload["snapshot_time"] == "2025-09-22T15:00:00Z"
    assert payload["advisory_count"] == 4
    assert len(payload["advisories"]) == payload["advisory_count"]


def test_advisories_are_facility_level_and_sorted():
    payload = load_output()
    advisories = payload["advisories"]

    assert advisories == [
        {
            "park_id": "PARK-106",
            "station_id": "08150000",
            "flood_stage_ft": 9.5,
            "observed_stage_ft": 11.1,
            "exceedance_ft": 1.6,
        },
        {
            "park_id": "PARK-101",
            "station_id": "08100000",
            "flood_stage_ft": 18.0,
            "observed_stage_ft": 19.4,
            "exceedance_ft": 1.4,
        },
        {
            "park_id": "PARK-105",
            "station_id": "08100000",
            "flood_stage_ft": 18.0,
            "observed_stage_ft": 19.4,
            "exceedance_ft": 1.4,
        },
        {
            "park_id": "PARK-104",
            "station_id": "08130000",
            "flood_stage_ft": 15.0,
            "observed_stage_ft": 15.0,
            "exceedance_ft": 0.0,
        },
    ]


def test_non_flood_and_invalid_threshold_parks_are_excluded():
    payload = load_output()
    park_ids = {row["park_id"] for row in payload["advisories"]}

    assert "PARK-102" not in park_ids
    assert "PARK-103" not in park_ids
    assert "PARK-107" not in park_ids
    assert "PARK-108" not in park_ids
