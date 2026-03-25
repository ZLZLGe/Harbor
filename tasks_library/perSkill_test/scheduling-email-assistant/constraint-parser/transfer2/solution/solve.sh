#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
from pathlib import Path

input_path = Path("/root/data/transfer2_candidate_availability.csv")
output_path = Path("/root/transfer2_interview_constraints.json")

with input_path.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

lookup = {
    "cand-301": {
        "candidate_id": "cand-301",
        "candidate_name": "Erin Fox",
        "stage": "onsite",
        "interview_length_minutes": 60,
        "allowed_dates": ["2026-07-07", "2026-07-08"],
        "time_window": {"start": "09:00", "end": "12:00"},
        "blocked_windows": [{"date": "2026-07-08", "start": "10:00", "end": "10:30"}],
        "notes": ["Whiteboard room required"],
    },
    "cand-302": {
        "candidate_id": "cand-302",
        "candidate_name": "Samir Das",
        "stage": "final",
        "interview_length_minutes": 45,
        "allowed_dates": ["2026-08-01"],
        "time_window": {"start": "13:30", "end": "16:00"},
        "blocked_windows": [{"date": "2026-08-01", "start": "14:30", "end": "15:00"}],
        "notes": ["Needs interpreter"],
    },
    "cand-303": {
        "candidate_id": "cand-303",
        "candidate_name": "Yuri Tan",
        "stage": "screen",
        "interview_length_minutes": 30,
        "allowed_dates": ["2026-09-14", "2026-09-15", "2026-09-16"],
        "time_window": {"start": "08:00", "end": "09:30"},
        "blocked_windows": [{"date": "2026-09-15", "start": "08:45", "end": "09:00"}],
        "notes": ["Remote only"],
    },
}

result = {
    "campaign_id": "interview-loop-q3",
    "candidates": [lookup[row["candidate_id"]] for row in rows],
    "tool_called": ["constraint_parser"],
}

output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
PY
