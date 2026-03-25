import json
from pathlib import Path


OUTPUT = Path("/root/transfer2_interview_constraints.json")

EXPECTED = {
    "campaign_id": "interview-loop-q3",
    "candidates": [
        {
            "candidate_id": "cand-301",
            "candidate_name": "Erin Fox",
            "stage": "onsite",
            "interview_length_minutes": 60,
            "allowed_dates": ["2026-07-07", "2026-07-08"],
            "time_window": {"start": "09:00", "end": "12:00"},
            "blocked_windows": [{"date": "2026-07-08", "start": "10:00", "end": "10:30"}],
            "notes": ["Whiteboard room required"],
        },
        {
            "candidate_id": "cand-302",
            "candidate_name": "Samir Das",
            "stage": "final",
            "interview_length_minutes": 45,
            "allowed_dates": ["2026-08-01"],
            "time_window": {"start": "13:30", "end": "16:00"},
            "blocked_windows": [{"date": "2026-08-01", "start": "14:30", "end": "15:00"}],
            "notes": ["Needs interpreter"],
        },
        {
            "candidate_id": "cand-303",
            "candidate_name": "Yuri Tan",
            "stage": "screen",
            "interview_length_minutes": 30,
            "allowed_dates": ["2026-09-14", "2026-09-15", "2026-09-16"],
            "time_window": {"start": "08:00", "end": "09:30"},
            "blocked_windows": [{"date": "2026-09-15", "start": "08:45", "end": "09:00"}],
            "notes": ["Remote only"],
        },
    ],
    "tool_called": ["constraint_parser"],
}


def test_output_exists():
    assert OUTPUT.exists(), "missing transfer2 output"


def test_output_matches_expected_payload():
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert actual == EXPECTED


def test_dates_expand_in_expected_order():
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert actual["candidates"][0]["allowed_dates"] == ["2026-07-07", "2026-07-08"]
    assert actual["candidates"][2]["notes"] == ["Remote only"]
