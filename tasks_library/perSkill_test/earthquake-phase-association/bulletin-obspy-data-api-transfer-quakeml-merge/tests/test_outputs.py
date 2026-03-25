import csv
from datetime import datetime
from pathlib import Path


EXPECTED_ORDER = [
    "rgn-240401-01",
    "rgn-240401-02",
    "rgn-240401-03",
    "rgn-240401-04",
    "rgn-240401-05",
]

EXPECTED_ROWS = {
    "rgn-240401-01": {
        "time": "2024-04-01T00:15:12.600000",
        "latitude": 61.246,
        "longitude": -149.810,
        "depth_km": 33.5,
        "magnitude": 3.6,
        "magnitude_type": "MLv",
        "source_count": 2,
    },
    "rgn-240401-02": {
        "time": "2024-04-01T01:02:33.450000",
        "latitude": 60.103,
        "longitude": -152.224,
        "depth_km": 12.0,
        "magnitude": 2.9,
        "magnitude_type": "Md",
        "source_count": 2,
    },
    "rgn-240401-03": {
        "time": "2024-04-01T02:45:01.850000",
        "latitude": 59.882,
        "longitude": -150.444,
        "depth_km": 18.6,
        "magnitude": 4.2,
        "magnitude_type": "Mw",
        "source_count": 2,
    },
    "rgn-240401-04": {
        "time": "2024-04-01T04:11:10.000000",
        "latitude": 58.442,
        "longitude": -151.991,
        "depth_km": 5.6,
        "magnitude": 1.7,
        "magnitude_type": "ML",
        "source_count": 1,
    },
    "rgn-240401-05": {
        "time": "2024-04-01T06:20:44.250000",
        "latitude": 57.930,
        "longitude": -153.774,
        "depth_km": 22.1,
        "magnitude": 3.1,
        "magnitude_type": "ML",
        "source_count": 1,
    },
}


def load_rows():
    output_path = Path("/root/regional_bulletin.csv")
    assert output_path.exists(), "missing /root/regional_bulletin.csv"
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_contract_and_sort_order():
    rows = load_rows()
    assert rows, "output CSV must not be empty"
    assert len(rows) == 5, "expected one bulletin row per unique merged event"
    assert list(rows[0].keys()) == [
        "event_id",
        "time",
        "latitude",
        "longitude",
        "depth_km",
        "magnitude",
        "magnitude_type",
        "source_count",
    ], "output columns must exactly match the required eight columns"

    event_ids = [row["event_id"] for row in rows]
    assert event_ids == EXPECTED_ORDER, "rows must be sorted by time ascending and tie-broken by event_id"
    assert len(set(event_ids)) == len(event_ids), "event_id values must be unique after deduplication"

    parsed_times = [datetime.fromisoformat(row["time"]) for row in rows]
    assert parsed_times == sorted(parsed_times), "time values must be sorted ascending"
    assert all(item.tzinfo is None for item in parsed_times), "time values must not contain timezone suffixes"


def test_focus_event_values():
    rows = load_rows()
    row_map = {row["event_id"]: row for row in rows}

    for event_id, expected in EXPECTED_ROWS.items():
        row = row_map.get(event_id)
        assert row is not None, f"missing merged row for {event_id}"
        assert row["time"] == expected["time"]
        assert abs(float(row["latitude"]) - expected["latitude"]) < 1e-6
        assert abs(float(row["longitude"]) - expected["longitude"]) < 1e-6
        assert abs(float(row["depth_km"]) - expected["depth_km"]) < 1e-6
        assert abs(float(row["magnitude"]) - expected["magnitude"]) < 1e-6
        assert row["magnitude_type"] == expected["magnitude_type"]
        assert int(row["source_count"]) == expected["source_count"]
