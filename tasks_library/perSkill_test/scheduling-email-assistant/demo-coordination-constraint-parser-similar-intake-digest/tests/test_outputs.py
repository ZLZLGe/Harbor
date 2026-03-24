import json
from pathlib import Path


OUTPUT_PATH = Path("/root/demo_request_constraints.json")

EXPECTED_OUTPUT = {
    "requests": [
        {
            "request_id": "demo-001",
            "requester_email": "alina@northstarhealth.com",
            "timezone_reference": "Eastern Time",
            "session_duration_minutes": 45,
            "acceptable_date_ranges": [
                {"start_date": "2026-04-14", "end_date": "2026-04-16"}
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
        {
            "request_id": "demo-002",
            "requester_email": "mina@brightlane.io",
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
        {
            "request_id": "demo-003",
            "requester_email": "owen@harborsideops.co.uk",
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
        {
            "request_id": "demo-004",
            "requester_email": "priya@fultonprocurement.com",
            "timezone_reference": "Central Time",
            "session_duration_minutes": 60,
            "acceptable_date_ranges": [
                {"start_date": "2026-05-04", "end_date": "2026-05-06"}
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
    ]
}


def main():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"

    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        actual = json.load(f)

    assert actual == EXPECTED_OUTPUT, (
        "Output JSON did not match the expected normalized constraints.\n"
        f"Expected: {json.dumps(EXPECTED_OUTPUT, indent=2)}\n"
        f"Actual: {json.dumps(actual, indent=2)}"
    )

    print("Output matches expected demo constraint digest.")


if __name__ == "__main__":
    main()
