import csv
import os


OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH", "/root/output/station_threshold_catalog.csv"
)


def load_rows():
    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), (
        "CSV file not found at /root/output/station_threshold_catalog.csv"
    )


def test_output_matches_expected_catalog():
    rows = load_rows()
    assert rows, "Output CSV is empty"
    assert list(rows[0].keys()) == [
        "station_id",
        "location_name",
        "state",
        "action_stage",
        "flood_stage",
        "moderate_stage",
        "major_stage",
    ]

    normalized = [
        {
            "station_id": row["station_id"],
            "location_name": row["location_name"],
            "state": row["state"],
            "action_stage": float(row["action_stage"]),
            "flood_stage": float(row["flood_stage"]),
            "moderate_stage": float(row["moderate_stage"]),
            "major_stage": float(row["major_stage"]),
        }
        for row in rows
    ]

    assert normalized == [
        {
            "station_id": "05512000",
            "location_name": "Mill Creek at Oak Junction",
            "state": "IL",
            "action_stage": 8.5,
            "flood_stage": 10.0,
            "moderate_stage": 12.5,
            "major_stage": 15.0,
        },
        {
            "station_id": "05513000",
            "location_name": "Cedar Run near Milburn",
            "state": "IL",
            "action_stage": 7.0,
            "flood_stage": 9.5,
            "moderate_stage": 11.0,
            "major_stage": 13.0,
        },
        {
            "station_id": "05530000",
            "location_name": "South Branch at Elgin",
            "state": "IL",
            "action_stage": 9.0,
            "flood_stage": 11.5,
            "moderate_stage": 13.5,
            "major_stage": 16.0,
        },
        {
            "station_id": "05531000",
            "location_name": "Quarry Creek nr. Benton",
            "state": "MO",
            "action_stage": 10.0,
            "flood_stage": 12.0,
            "moderate_stage": 14.0,
            "major_stage": 17.0,
        },
        {
            "station_id": "05532000",
            "location_name": "Prairie Ditch at Moberly",
            "state": "MO",
            "action_stage": 4.0,
            "flood_stage": 6.0,
            "moderate_stage": 7.5,
            "major_stage": 9.0,
        },
    ]


def test_invalid_and_unmatched_records_are_excluded():
    station_ids = {row["station_id"] for row in load_rows()}

    assert "05525500" not in station_ids
    assert "05530500" not in station_ids
    assert "05533000" not in station_ids


def test_roster_duplicates_are_deduplicated_in_output():
    rows = load_rows()
    station_ids = [row["station_id"] for row in rows]
    assert station_ids.count("05513000") == 1
    assert station_ids.count("05530000") == 1
