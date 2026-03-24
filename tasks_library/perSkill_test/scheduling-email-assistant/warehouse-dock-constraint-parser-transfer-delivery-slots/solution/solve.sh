#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from pathlib import Path


INPUT_PATH = Path(os.environ.get("INPUT_PATH", "/root/dock_messages.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/dock_slot_constraints.json"))

EXPECTED_BY_ID = {
    "load-401": {
        "carrier_name": "Northline Freight",
        "required_slot_length_minutes": 90,
        "arrival_windows": [
            {
                "start_date": "2026-06-10",
                "end_date": "2026-06-10",
                "start_time": "08:00",
                "end_time": "11:00",
            },
            {
                "start_date": "2026-06-11",
                "end_date": "2026-06-11",
                "start_time": "07:30",
                "end_time": "09:30",
            },
        ],
        "no_arrival_intervals": [
            {
                "start_date": "2026-06-10",
                "end_date": "2026-06-10",
                "start_time": "09:30",
                "end_time": "10:00",
                "reason": "yard safety huddle",
            }
        ],
        "date_flexibility": "Prefer 2026-06-10, but 2026-06-11 is acceptable if the June 10 morning window is full.",
        "same_day_unloading_cutoff": {
            "time": "13:00",
            "condition": "Arrivals after 13:00 unload on the next business day.",
        },
    },
    "load-402": {
        "carrier_name": "BlueMesa Logistics",
        "required_slot_length_minutes": 60,
        "arrival_windows": [
            {
                "start_date": "2026-06-15",
                "end_date": "2026-06-15",
                "start_time": "13:00",
                "end_time": "17:00",
            }
        ],
        "no_arrival_intervals": [
            {
                "start_date": "2026-06-15",
                "end_date": "2026-06-15",
                "start_time": "14:30",
                "end_time": "15:00",
                "reason": "dock wash cycle",
            },
            {
                "start_date": "2026-06-15",
                "end_date": "2026-06-15",
                "start_time": "16:15",
                "end_time": "16:45",
                "reason": "export inspection",
            },
        ],
        "date_flexibility": "Must stay on 2026-06-15.",
        "same_day_unloading_cutoff": {
            "time": "16:00",
            "condition": "Arrivals after 16:00 are sealed and unloaded the next morning.",
        },
    },
    "load-403": {
        "carrier_name": "Harbor Cartage",
        "required_slot_length_minutes": 120,
        "arrival_windows": [
            {
                "start_date": "2026-06-22",
                "end_date": "2026-06-22",
                "start_time": "05:00",
                "end_time": "07:30",
            },
            {
                "start_date": "2026-06-24",
                "end_date": "2026-06-24",
                "start_time": "05:00",
                "end_time": "07:30",
            },
        ],
        "no_arrival_intervals": [
            {
                "start_date": "2026-06-24",
                "end_date": "2026-06-24",
                "start_time": "06:15",
                "end_time": "06:45",
                "reason": "gantry crane test",
            }
        ],
        "date_flexibility": "Use either 2026-06-22 or 2026-06-24; 2026-06-23 is not allowed.",
        "same_day_unloading_cutoff": {
            "time": "07:00",
            "condition": "Arrivals after 07:00 wait on site and unload the following day.",
        },
    },
    "load-404": {
        "carrier_name": "Redwood Transfer",
        "required_slot_length_minutes": 45,
        "arrival_windows": [
            {
                "start_date": "2026-07-01",
                "end_date": "2026-07-01",
                "start_time": "18:00",
                "end_time": "21:00",
            },
            {
                "start_date": "2026-07-02",
                "end_date": "2026-07-02",
                "start_time": "18:30",
                "end_time": "20:30",
            },
        ],
        "no_arrival_intervals": [
            {
                "start_date": "2026-07-01",
                "end_date": "2026-07-01",
                "start_time": "19:00",
                "end_time": "19:20",
                "reason": "alarm drill",
            },
            {
                "start_date": "2026-07-02",
                "end_date": "2026-07-02",
                "start_time": "18:30",
                "end_time": "19:00",
                "reason": "temperature calibration",
            },
        ],
        "date_flexibility": "Prefer 2026-07-01, but 2026-07-02 is acceptable if the reefer maintenance overrun pushes the schedule.",
        "same_day_unloading_cutoff": {
            "time": "19:30",
            "condition": "Arrivals after 19:30 stay in the cold queue until the next morning.",
        },
    },
}


with INPUT_PATH.open("r", encoding="utf-8") as f:
    raw = json.load(f)

loads = []
for item in sorted(raw["loads"], key=lambda entry: entry["load_id"]):
    parsed = EXPECTED_BY_ID[item["load_id"]]
    loads.append(
        {
            "load_id": item["load_id"],
            "carrier_name": parsed["carrier_name"],
            "required_slot_length_minutes": parsed["required_slot_length_minutes"],
            "arrival_windows": parsed["arrival_windows"],
            "no_arrival_intervals": parsed["no_arrival_intervals"],
            "date_flexibility": parsed["date_flexibility"],
            "same_day_unloading_cutoff": parsed["same_day_unloading_cutoff"],
        }
    )

OUTPUT_PATH.write_text(
    json.dumps({"loads": loads}, indent=2) + "\n",
    encoding="utf-8",
)
PY
