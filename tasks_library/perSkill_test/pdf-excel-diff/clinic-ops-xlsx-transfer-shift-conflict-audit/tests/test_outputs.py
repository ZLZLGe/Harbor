#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_FILE = Path("/root/clinic_shift_conflicts.json")

EXPECTED_OUTPUT = {
    "double_booked_staff": [
        {
            "staff_id": "S-003",
            "staff_name": "Ava Lin",
            "date": "2026-04-14",
            "first_shift_id": "CL-1003",
            "first_room": "Lab A",
            "first_start_time": "09:30",
            "first_end_time": "13:00",
            "second_shift_id": "CL-1004",
            "second_room": "Imaging",
            "second_start_time": "12:00",
            "second_end_time": "16:00",
        },
        {
            "staff_id": "S-004",
            "staff_name": "Leo Chen",
            "date": "2026-04-15",
            "first_shift_id": "CL-1008",
            "first_room": "Lab A",
            "first_start_time": "13:00",
            "first_end_time": "17:00",
            "second_shift_id": "CL-1009",
            "second_room": "Imaging",
            "second_start_time": "13:00",
            "second_end_time": "17:00",
        },
    ],
    "unavailable_assignments": [
        {
            "shift_id": "CL-1006",
            "staff_id": "S-005",
            "staff_name": "Maya Gomez",
            "date": "2026-04-15",
            "room": "Pediatrics",
            "shift_start_time": "08:00",
            "shift_end_time": "12:00",
            "unavailable_start_time": "10:00",
            "unavailable_end_time": "12:00",
        },
        {
            "shift_id": "CL-1007",
            "staff_id": "S-001",
            "staff_name": "Nina Patel",
            "date": "2026-04-15",
            "room": "Exam 1",
            "shift_start_time": "08:00",
            "shift_end_time": "12:00",
            "unavailable_start_time": "08:00",
            "unavailable_end_time": "12:00",
        },
    ],
    "uncovered_shifts": [
        {
            "shift_id": "CL-1005",
            "date": "2026-04-14",
            "room": "Triage",
            "start_time": "13:00",
            "end_time": "17:00",
            "required_staff": 2,
            "assigned_staff": 1,
            "missing_staff": 1,
        }
    ],
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_sorted(items: list[dict[str, object]], key_fn, message: str) -> None:
    assert_true(items == sorted(items, key=key_fn), message)


def main() -> None:
    assert_true(OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}")

    with OUTPUT_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)

    assert_true(
        set(data.keys()) == {"double_booked_staff", "unavailable_assignments", "uncovered_shifts"},
        "Output keys do not match the expected schema",
    )
    assert_true(data == EXPECTED_OUTPUT, "Output content does not match the expected clinic conflict report")

    assert_sorted(
        data["double_booked_staff"],
        lambda item: (item["staff_id"], item["date"], item["first_shift_id"], item["second_shift_id"]),
        "double_booked_staff is not correctly sorted",
    )
    assert_sorted(
        data["unavailable_assignments"],
        lambda item: (item["shift_id"], item["staff_id"]),
        "unavailable_assignments is not correctly sorted",
    )
    assert_sorted(
        data["uncovered_shifts"],
        lambda item: item["shift_id"],
        "uncovered_shifts is not correctly sorted",
    )

    for item in data["double_booked_staff"]:
        assert_true(isinstance(item["staff_id"], str), "staff_id must be a string")
        assert_true(isinstance(item["date"], str), "date must be a string")

    for item in data["uncovered_shifts"]:
        for field in ("required_staff", "assigned_staff", "missing_staff"):
            assert_true(isinstance(item[field], int), f"{field} must be an integer")


if __name__ == "__main__":
    main()
