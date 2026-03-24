#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from pathlib import Path


INPUT_PATH = Path(os.environ.get("INPUT_PATH", "/root/patient_callbacks.json"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/clinic_followup_constraints.json"))

EXPECTED_BY_ID = {
    "followup-001": {
        "patient_name": "Ana Morales",
        "visit_duration_minutes": 30,
        "allowed_days": ["Monday", "Wednesday"],
        "preferred_visit_windows": [
            {
                "days": ["Monday", "Wednesday"],
                "start_time": "08:00",
                "end_time": "11:00",
            }
        ],
        "no_visit_dates": [
            {"date": "2026-05-06", "reason": "traveling"}
        ],
        "timing_conditions": [
            "Schedule at least 48 hours after the last iron infusion on 2026-05-03.",
            "Patient must fast for 8 hours before the visit.",
        ],
    },
    "followup-002": {
        "patient_name": "Benita Shah",
        "visit_duration_minutes": 45,
        "allowed_days": ["Tuesday", "Thursday"],
        "preferred_visit_windows": [
            {
                "days": ["Tuesday", "Thursday"],
                "start_time": "13:30",
                "end_time": "16:00",
            }
        ],
        "no_visit_dates": [
            {"date": "2026-05-12", "reason": "daughter's graduation"}
        ],
        "timing_conditions": [
            "Schedule no sooner than 7 days after cast removal on 2026-05-05."
        ],
    },
    "followup-003": {
        "patient_name": "Carl Nguyen",
        "visit_duration_minutes": 20,
        "allowed_days": ["Friday"],
        "preferred_visit_windows": [
            {
                "days": ["Friday"],
                "start_time": "09:00",
                "end_time": "10:30",
            }
        ],
        "no_visit_dates": [
            {"date": "2026-05-22", "reason": "school field trip"},
            {"date": "2026-05-29", "reason": "out of town"},
        ],
        "timing_conditions": [
            "Schedule within 3 days after the MRI on 2026-05-20."
        ],
    },
    "followup-004": {
        "patient_name": "Dana Brooks",
        "visit_duration_minutes": 60,
        "allowed_days": ["Monday", "Tuesday", "Friday"],
        "preferred_visit_windows": [
            {
                "days": ["Monday", "Friday"],
                "start_time": "14:00",
                "end_time": "17:00",
            },
            {
                "days": ["Tuesday"],
                "start_time": "15:00",
                "end_time": "17:00",
            },
        ],
        "no_visit_dates": [
            {"date": "2026-06-02", "reason": "dialysis"}
        ],
        "timing_conditions": [
            "Schedule at least 14 days after the steroid taper ended on 2026-05-18.",
            "Patient must not eat for 6 hours before the visit.",
        ],
    },
}


with INPUT_PATH.open("r", encoding="utf-8") as f:
    raw = json.load(f)

callbacks = []
for item in sorted(raw["callbacks"], key=lambda entry: entry["callback_id"]):
    callback_id = item["callback_id"]
    expected = EXPECTED_BY_ID[callback_id]
    callbacks.append(
        {
            "callback_id": callback_id,
            "patient_name": expected["patient_name"],
            "visit_duration_minutes": expected["visit_duration_minutes"],
            "allowed_days": expected["allowed_days"],
            "preferred_visit_windows": expected["preferred_visit_windows"],
            "no_visit_dates": expected["no_visit_dates"],
            "timing_conditions": expected["timing_conditions"],
        }
    )

OUTPUT_PATH.write_text(
    json.dumps({"callbacks": callbacks}, indent=2) + "\n",
    encoding="utf-8",
)
PY
