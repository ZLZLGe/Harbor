#!/bin/bash
set -euo pipefail

cat > /tmp/solve_clinic_shift_conflicts.py <<'PYTHON'
#!/usr/bin/env python3

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import load_workbook

WORKBOOK_FILE = Path("/root/clinic_staffing.xlsx")
OUTPUT_FILE = Path("/root/clinic_shift_conflicts.json")


def normalize_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def format_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def format_time(value: object) -> str:
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)


def minutes(value: object) -> int:
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, str):
        parsed = time.fromisoformat(value)
        return parsed.hour * 60 + parsed.minute
    raise TypeError(f"Unsupported time value: {value!r}")


def find_header_row(worksheet, required_headers: set[str]) -> tuple[int, dict[str, int]]:
    for row_number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
        headers = {
            normalize_text(cell): index
            for index, cell in enumerate(row)
            if normalize_text(cell)
        }
        if required_headers.issubset(headers.keys()):
            return row_number, headers
    raise RuntimeError(f"Could not find headers {sorted(required_headers)} in sheet {worksheet.title}")


def extract_rows(worksheet, required_headers: set[str], key_header: str) -> list[dict[str, object]]:
    header_row, header_map = find_header_row(worksheet, required_headers)
    extracted = []
    for row in worksheet.iter_rows(min_row=header_row + 1, values_only=True):
        key_index = header_map[key_header]
        key_value = row[key_index] if key_index < len(row) else None
        if key_value is None or normalize_text(key_value) == "":
            continue
        item = {}
        for header in required_headers:
            index = header_map[header]
            item[header] = row[index] if index < len(row) else None
        extracted.append(item)
    return extracted


def overlaps(start_a: object, end_a: object, start_b: object, end_b: object) -> bool:
    return max(minutes(start_a), minutes(start_b)) < min(minutes(end_a), minutes(end_b))


def main() -> None:
    workbook = load_workbook(WORKBOOK_FILE, data_only=True)

    availability_rows = extract_rows(
        workbook["Availability"],
        {"Staff ID", "Staff Name", "Date", "Start Time", "End Time", "Reason"},
        "Staff ID",
    )
    assignment_rows = extract_rows(
        workbook["Assignments"],
        {"Shift ID", "Date", "Start Time", "End Time", "Room", "Role", "Staff ID", "Staff Name"},
        "Shift ID",
    )
    coverage_rows = extract_rows(
        workbook["Room Coverage"],
        {"Shift ID", "Date", "Start Time", "End Time", "Room", "Required Staff"},
        "Shift ID",
    )

    assignments_by_staff = defaultdict(list)
    assignments_by_shift = defaultdict(list)
    blackout_by_staff = defaultdict(list)

    for row in assignment_rows:
        record = {
            "shift_id": normalize_text(row["Shift ID"]),
            "date": format_date(row["Date"]),
            "start_time": format_time(row["Start Time"]),
            "end_time": format_time(row["End Time"]),
            "room": normalize_text(row["Room"]),
            "staff_id": normalize_text(row["Staff ID"]),
            "staff_name": normalize_text(row["Staff Name"]),
        }
        assignments_by_staff[(record["staff_id"], record["date"])].append(record)
        assignments_by_shift[record["shift_id"]].append(record)

    for row in availability_rows:
        record = {
            "staff_id": normalize_text(row["Staff ID"]),
            "date": format_date(row["Date"]),
            "start_time": format_time(row["Start Time"]),
            "end_time": format_time(row["End Time"]),
        }
        blackout_by_staff[(record["staff_id"], record["date"])].append(record)

    double_booked = []
    for (_staff_id, _date), records in assignments_by_staff.items():
        ordered = sorted(records, key=lambda item: (item["start_time"], item["end_time"], item["shift_id"]))
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if overlaps(first["start_time"], first["end_time"], second["start_time"], second["end_time"]):
                    double_booked.append(
                        {
                            "staff_id": first["staff_id"],
                            "staff_name": first["staff_name"],
                            "date": first["date"],
                            "first_shift_id": first["shift_id"],
                            "first_room": first["room"],
                            "first_start_time": first["start_time"],
                            "first_end_time": first["end_time"],
                            "second_shift_id": second["shift_id"],
                            "second_room": second["room"],
                            "second_start_time": second["start_time"],
                            "second_end_time": second["end_time"],
                        }
                    )

    unavailable_assignments = []
    for records in assignments_by_staff.values():
        for assignment in records:
            blackouts = blackout_by_staff.get((assignment["staff_id"], assignment["date"]), [])
            for blackout in blackouts:
                if overlaps(
                    assignment["start_time"],
                    assignment["end_time"],
                    blackout["start_time"],
                    blackout["end_time"],
                ):
                    unavailable_assignments.append(
                        {
                            "shift_id": assignment["shift_id"],
                            "staff_id": assignment["staff_id"],
                            "staff_name": assignment["staff_name"],
                            "date": assignment["date"],
                            "room": assignment["room"],
                            "shift_start_time": assignment["start_time"],
                            "shift_end_time": assignment["end_time"],
                            "unavailable_start_time": blackout["start_time"],
                            "unavailable_end_time": blackout["end_time"],
                        }
                    )

    uncovered_shifts = []
    for row in coverage_rows:
        shift_id = normalize_text(row["Shift ID"])
        required_staff = int(row["Required Staff"])
        assigned_staff = len(assignments_by_shift.get(shift_id, []))
        if assigned_staff < required_staff:
            uncovered_shifts.append(
                {
                    "shift_id": shift_id,
                    "date": format_date(row["Date"]),
                    "room": normalize_text(row["Room"]),
                    "start_time": format_time(row["Start Time"]),
                    "end_time": format_time(row["End Time"]),
                    "required_staff": required_staff,
                    "assigned_staff": assigned_staff,
                    "missing_staff": required_staff - assigned_staff,
                }
            )

    result = {
        "double_booked_staff": sorted(
            double_booked,
            key=lambda item: (item["staff_id"], item["date"], item["first_shift_id"], item["second_shift_id"]),
        ),
        "unavailable_assignments": sorted(
            unavailable_assignments,
            key=lambda item: (item["shift_id"], item["staff_id"]),
        ),
        "uncovered_shifts": sorted(uncovered_shifts, key=lambda item: item["shift_id"]),
    }

    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
PYTHON

python3 /tmp/solve_clinic_shift_conflicts.py
