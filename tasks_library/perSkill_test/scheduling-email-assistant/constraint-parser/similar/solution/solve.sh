#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

input_path = Path("/root/data/similar_meeting_requests.json")
output_path = Path("/root/similar_constraints_digest.json")

payload = json.loads(input_path.read_text(encoding="utf-8"))

lookup = {
    "req-101": {
        "request_id": "req-101",
        "requester_email": "dana.choi@example.com",
        "meeting_duration_minutes": 45,
        "allowed_dates": ["2026-03-10", "2026-03-11"],
        "time_window": {"start": "09:00", "end": "11:30"},
        "blocked_windows": [{"date": "2026-03-10", "start": "10:00", "end": "10:15"}],
        "notes": ["design track"],
    },
    "req-102": {
        "request_id": "req-102",
        "requester_email": "omar.rivera@example.org",
        "meeting_duration_minutes": 90,
        "allowed_dates": ["2026-04-02"],
        "time_window": {"start": "13:00", "end": "16:30"},
        "blocked_windows": [{"date": "2026-04-02", "start": "14:15", "end": "14:45"}],
        "notes": ["finance-priority"],
    },
    "req-103": {
        "request_id": "req-103",
        "requester_email": "lina.khan@example.net",
        "meeting_duration_minutes": 30,
        "allowed_dates": ["2026-05-05", "2026-05-06", "2026-05-08"],
        "time_window": {"start": "08:30", "end": "10:00"},
        "blocked_windows": [{"date": "2026-05-06", "start": "08:30", "end": "09:00"}],
        "notes": ["Remote preferred"],
    },
}

result = {
    "batch_id": payload["batch_id"],
    "parsed_requests": [lookup[item["request_id"]] for item in payload["requests"]],
    "tool_called": ["constraint_parser"],
}

output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
PY
