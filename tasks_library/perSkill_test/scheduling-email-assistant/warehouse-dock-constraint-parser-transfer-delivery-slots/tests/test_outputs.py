import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/dock_slot_constraints.json"))

EXPECTED = {
    "load-401": {
        "carrier_name": "Northline Freight",
        "required_slot_length_minutes": 90,
        "arrival_windows": [
            ("2026-06-10", "08:00", "11:00"),
            ("2026-06-11", "07:30", "09:30"),
        ],
        "no_arrival_intervals": [
            ("2026-06-10", "09:30", "10:00", "yard safety huddle")
        ],
        "date_flexibility": "Prefer 2026-06-10, but 2026-06-11 is acceptable if the June 10 morning window is full.",
        "cutoff_time": "13:00",
        "cutoff_condition": "Arrivals after 13:00 unload on the next business day.",
        "forbidden_dates": {"2026-06-09"},
    },
    "load-402": {
        "carrier_name": "BlueMesa Logistics",
        "required_slot_length_minutes": 60,
        "arrival_windows": [
            ("2026-06-15", "13:00", "17:00")
        ],
        "no_arrival_intervals": [
            ("2026-06-15", "14:30", "15:00", "dock wash cycle"),
            ("2026-06-15", "16:15", "16:45", "export inspection"),
        ],
        "date_flexibility": "Must stay on 2026-06-15.",
        "cutoff_time": "16:00",
        "cutoff_condition": "Arrivals after 16:00 are sealed and unloaded the next morning.",
        "forbidden_dates": set(),
    },
    "load-403": {
        "carrier_name": "Harbor Cartage",
        "required_slot_length_minutes": 120,
        "arrival_windows": [
            ("2026-06-22", "05:00", "07:30"),
            ("2026-06-24", "05:00", "07:30"),
        ],
        "no_arrival_intervals": [
            ("2026-06-24", "06:15", "06:45", "gantry crane test")
        ],
        "date_flexibility": "Use either 2026-06-22 or 2026-06-24; 2026-06-23 is not allowed.",
        "cutoff_time": "07:00",
        "cutoff_condition": "Arrivals after 07:00 wait on site and unload the following day.",
        "forbidden_dates": {"2026-06-23"},
    },
    "load-404": {
        "carrier_name": "Redwood Transfer",
        "required_slot_length_minutes": 45,
        "arrival_windows": [
            ("2026-07-01", "18:00", "21:00"),
            ("2026-07-02", "18:30", "20:30"),
        ],
        "no_arrival_intervals": [
            ("2026-07-01", "19:00", "19:20", "alarm drill"),
            ("2026-07-02", "18:30", "19:00", "temperature calibration"),
        ],
        "date_flexibility": "Prefer 2026-07-01, but 2026-07-02 is acceptable if the reefer maintenance overrun pushes the schedule.",
        "cutoff_time": "19:30",
        "cutoff_condition": "Arrivals after 19:30 stay in the cold queue until the next morning.",
        "forbidden_dates": set(),
    },
}


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def to_window_tuples(items):
    return [
        (item["start_date"], item["start_time"], item["end_time"])
        for item in items
    ]


def to_block_tuples(items):
    return [
        (item["start_date"], item["start_time"], item["end_time"], item["reason"])
        for item in items
    ]


def test_schema_and_values():
    actual = load_output()
    assert list(actual.keys()) == ["loads"], "Top-level JSON must only contain 'loads'."

    loads = actual["loads"]
    ids = [entry["load_id"] for entry in loads]
    assert ids == sorted(EXPECTED), "Loads must be sorted by load_id."
    assert len(loads) == len(EXPECTED), "Unexpected number of load summaries."

    for entry in loads:
        load_id = entry["load_id"]
        assert load_id in EXPECTED, f"Unexpected load_id: {load_id}"
        expected = EXPECTED[load_id]

        assert entry["carrier_name"] == expected["carrier_name"]
        assert entry["required_slot_length_minutes"] == expected["required_slot_length_minutes"]
        assert isinstance(entry["required_slot_length_minutes"], int)

        actual_windows = to_window_tuples(entry["arrival_windows"])
        actual_blocks = to_block_tuples(entry["no_arrival_intervals"])
        assert actual_windows == expected["arrival_windows"]
        assert actual_blocks == expected["no_arrival_intervals"]
        assert actual_windows == sorted(actual_windows), f"arrival_windows not sorted for {load_id}"
        assert actual_blocks == sorted(actual_blocks), f"no_arrival_intervals not sorted for {load_id}"

        assert entry["date_flexibility"] == expected["date_flexibility"]
        assert entry["date_flexibility"].endswith("."), f"date_flexibility must be a sentence for {load_id}"

        cutoff = entry["same_day_unloading_cutoff"]
        assert cutoff["time"] == expected["cutoff_time"]
        assert cutoff["condition"] == expected["cutoff_condition"]
        assert cutoff["condition"].endswith("."), f"cutoff condition must be a sentence for {load_id}"


def test_superseded_dates_do_not_leak():
    actual = load_output()["loads"]

    for entry in actual:
        load_id = entry["load_id"]
        forbidden_dates = EXPECTED[load_id]["forbidden_dates"]
        seen_dates = {
            window["start_date"] for window in entry["arrival_windows"]
        }
        assert forbidden_dates.isdisjoint(seen_dates), (
            f"Superseded or blocked dates leaked into arrival_windows for {load_id}: "
            f"{forbidden_dates & seen_dates}"
        )


if __name__ == "__main__":
    test_schema_and_values()
    test_superseded_dates_do_not_leak()
    print("Warehouse dock slot constraints verified.")
