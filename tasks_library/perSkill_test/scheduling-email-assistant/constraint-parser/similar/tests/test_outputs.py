import json
from pathlib import Path


OUTPUT = Path("/root/similar_constraints_digest.json")

EXPECTED = {
    "batch_id": "meeting-constraint-batch-03",
    "parsed_requests": [
        {
            "request_id": "req-101",
            "requester_email": "dana.choi@example.com",
            "meeting_duration_minutes": 45,
            "allowed_dates": ["2026-03-10", "2026-03-11"],
            "time_window": {"start": "09:00", "end": "11:30"},
            "blocked_windows": [{"date": "2026-03-10", "start": "10:00", "end": "10:15"}],
            "notes": ["design track"],
        },
        {
            "request_id": "req-102",
            "requester_email": "omar.rivera@example.org",
            "meeting_duration_minutes": 90,
            "allowed_dates": ["2026-04-02"],
            "time_window": {"start": "13:00", "end": "16:30"},
            "blocked_windows": [{"date": "2026-04-02", "start": "14:15", "end": "14:45"}],
            "notes": ["finance-priority"],
        },
        {
            "request_id": "req-103",
            "requester_email": "lina.khan@example.net",
            "meeting_duration_minutes": 30,
            "allowed_dates": ["2026-05-05", "2026-05-06", "2026-05-08"],
            "time_window": {"start": "08:30", "end": "10:00"},
            "blocked_windows": [{"date": "2026-05-06", "start": "08:30", "end": "09:00"}],
            "notes": ["Remote preferred"],
        },
    ],
    "tool_called": ["constraint_parser"],
}


def test_output_exists():
    assert OUTPUT.exists(), "missing similar output"


def test_output_matches_expected_payload():
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert actual == EXPECTED


def test_specific_blockers_and_order():
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert [item["request_id"] for item in actual["parsed_requests"]] == ["req-101", "req-102", "req-103"]
    assert actual["parsed_requests"][2]["blocked_windows"] == [
        {"date": "2026-05-06", "start": "08:30", "end": "09:00"}
    ]
