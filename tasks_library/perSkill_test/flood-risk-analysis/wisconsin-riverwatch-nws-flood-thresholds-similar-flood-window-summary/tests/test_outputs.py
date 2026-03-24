import csv
import os


OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH", "/root/output/wisconsin_flood_window.csv"
)


def load_rows():
    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), (
        "CSV file not found at /root/output/wisconsin_flood_window.csv"
    )


def test_output_schema_and_values():
    rows = load_rows()
    assert rows, "Output CSV is empty"
    assert list(rows[0].keys()) == [
        "station_id",
        "first_flood_date",
        "flood_days",
        "peak_stage_ft",
    ]

    normalized = [
        {
            "station_id": row["station_id"],
            "first_flood_date": row["first_flood_date"],
            "flood_days": int(row["flood_days"]),
            "peak_stage_ft": float(row["peak_stage_ft"]),
        }
        for row in rows
    ]

    assert normalized == [
        {
            "station_id": "05391000",
            "first_flood_date": "2025-06-10",
            "flood_days": 6,
            "peak_stage_ft": 21.0,
        },
        {
            "station_id": "05404000",
            "first_flood_date": "2025-06-11",
            "flood_days": 4,
            "peak_stage_ft": 15.4,
        },
        {
            "station_id": "05406500",
            "first_flood_date": "2025-06-12",
            "flood_days": 2,
            "peak_stage_ft": 10.2,
        },
        {
            "station_id": "05430175",
            "first_flood_date": "2025-06-12",
            "flood_days": 3,
            "peak_stage_ft": 10.0,
        },
    ]


def test_invalid_threshold_station_is_excluded():
    rows = load_rows()
    station_ids = {row["station_id"] for row in rows}
    assert "05429500" not in station_ids
