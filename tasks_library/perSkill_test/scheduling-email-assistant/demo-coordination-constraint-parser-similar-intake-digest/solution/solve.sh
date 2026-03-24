#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json

INPUT_PATH = "/root/demo_requests.json"
OUTPUT_PATH = "/root/demo_request_constraints.json"

REQUESTS = {
    "demo-001": {
        "timezone_reference": "Eastern Time",
        "session_duration_minutes": 45,
        "acceptable_date_ranges": [
            {"start_date": "2026-04-14", "end_date": "2026-04-16"},
        ],
        "preferred_time_windows": [
            {
                "start_date": "2026-04-14",
                "end_date": "2026-04-16",
                "start_time": "10:00",
                "end_time": "13:00",
            }
        ],
        "blackout_periods": [
            {
                "start_date": "2026-04-15",
                "end_date": "2026-04-15",
                "start_time": "11:30",
                "end_time": "12:00",
                "note": "CFO has a standing check-in",
            }
        ],
    },
    "demo-002": {
        "timezone_reference": "Pacific Time",
        "session_duration_minutes": 30,
        "acceptable_date_ranges": [
            {"start_date": "2026-04-20", "end_date": "2026-04-21"},
            {"start_date": "2026-04-23", "end_date": "2026-04-23"},
        ],
        "preferred_time_windows": [
            {
                "start_date": "2026-04-20",
                "end_date": "2026-04-21",
                "start_time": "14:00",
                "end_time": "17:00",
            },
            {
                "start_date": "2026-04-23",
                "end_date": "2026-04-23",
                "start_time": "09:00",
                "end_time": "11:00",
            },
        ],
        "blackout_periods": [
            {
                "start_date": "2026-04-22",
                "end_date": "2026-04-22",
                "start_time": None,
                "end_time": None,
                "note": "internal launch",
            }
        ],
    },
    "demo-003": {
        "timezone_reference": "BST",
        "session_duration_minutes": 90,
        "acceptable_date_ranges": [
            {"start_date": "2026-04-30", "end_date": "2026-04-30"},
            {"start_date": "2026-05-01", "end_date": "2026-05-01"},
        ],
        "preferred_time_windows": [
            {
                "start_date": "2026-04-30",
                "end_date": "2026-04-30",
                "start_time": "16:00",
                "end_time": "18:30",
            },
            {
                "start_date": "2026-05-01",
                "end_date": "2026-05-01",
                "start_time": "16:00",
                "end_time": "18:30",
            },
        ],
        "blackout_periods": [
            {
                "start_date": "2026-05-01",
                "end_date": "2026-05-01",
                "start_time": "17:00",
                "end_time": "17:30",
                "note": "shift handover",
            }
        ],
    },
    "demo-004": {
        "timezone_reference": "Central Time",
        "session_duration_minutes": 60,
        "acceptable_date_ranges": [
            {"start_date": "2026-05-04", "end_date": "2026-05-06"},
        ],
        "preferred_time_windows": [
            {
                "start_date": "2026-05-04",
                "end_date": "2026-05-06",
                "start_time": "08:30",
                "end_time": "10:30",
            }
        ],
        "blackout_periods": [],
    },
}

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    raw_requests = json.load(f)["requests"]

normalized = []
for request in sorted(raw_requests, key=lambda item: item["request_id"]):
    parsed = REQUESTS[request["request_id"]]
    normalized.append(
        {
            "request_id": request["request_id"],
            "requester_email": request["from_email"],
            "timezone_reference": parsed["timezone_reference"],
            "session_duration_minutes": parsed["session_duration_minutes"],
            "acceptable_date_ranges": parsed["acceptable_date_ranges"],
            "preferred_time_windows": parsed["preferred_time_windows"],
            "blackout_periods": parsed["blackout_periods"],
        }
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump({"requests": normalized}, f, indent=2)
    f.write("\n")
PY
