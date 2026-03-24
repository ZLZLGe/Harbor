import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/clinic_followup_constraints.json"))
WEEKDAY_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

EXPECTED = {
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


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_output_schema_and_values():
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        actual = json.load(f)

    assert list(actual.keys()) == ["callbacks"], "Top-level JSON must only contain 'callbacks'."

    callbacks = actual["callbacks"]
    ids = [entry["callback_id"] for entry in callbacks]
    assert ids == sorted(EXPECTED), "Callbacks must be sorted by callback_id."
    assert len(callbacks) == len(EXPECTED), "Unexpected number of callbacks."

    for entry in callbacks:
        callback_id = entry["callback_id"]
        assert callback_id in EXPECTED, f"Unexpected callback_id: {callback_id}"
        expected = EXPECTED[callback_id]

        assert entry["patient_name"] == expected["patient_name"]
        assert entry["visit_duration_minutes"] == expected["visit_duration_minutes"]
        assert isinstance(entry["visit_duration_minutes"], int)

        assert entry["allowed_days"] == expected["allowed_days"]
        assert entry["allowed_days"] == sorted(
            entry["allowed_days"], key=lambda day: WEEKDAY_ORDER[day]
        ), f"allowed_days not sorted for {callback_id}"

        assert entry["preferred_visit_windows"] == expected["preferred_visit_windows"]
        assert entry["no_visit_dates"] == expected["no_visit_dates"]
        assert [item["date"] for item in entry["no_visit_dates"]] == sorted(
            item["date"] for item in entry["no_visit_dates"]
        ), f"no_visit_dates not sorted for {callback_id}"

        assert entry["timing_conditions"] == expected["timing_conditions"]
        for condition in entry["timing_conditions"]:
            assert condition.endswith("."), f"Timing condition must be a sentence: {condition}"


if __name__ == "__main__":
    test_output_exists()
    test_output_schema_and_values()
    print("Clinic follow-up constraints verified.")
