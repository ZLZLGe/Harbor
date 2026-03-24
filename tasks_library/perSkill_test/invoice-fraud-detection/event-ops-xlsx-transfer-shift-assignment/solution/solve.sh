#!/bin/bash
set -euo pipefail

python3 <<'PY'
from collections import defaultdict

from openpyxl import load_workbook


INPUT_PATH = "/root/event_shift_template.xlsx"
OUTPUT_PATH = "/root/event_shift_plan.xlsx"


def iter_non_empty_rows(sheet, min_row):
    for row in sheet.iter_rows(min_row=min_row, values_only=True):
        if any(value not in (None, "") for value in row):
            yield row


workbook = load_workbook(INPUT_PATH)

roster_sheet = workbook["Volunteer Roster"]
availability_sheet = workbook["Availability Matrix"]
qualifications_sheet = workbook["Role Qualifications"]
demand_sheet = workbook["Shift Demand"]
assignments_sheet = workbook["Assignments"]
summary_sheet = workbook["Coverage Summary"]

roster = {}
for volunteer_id, volunteer_name, team, max_shifts, assignment_rank in iter_non_empty_rows(roster_sheet, 3):
    roster[volunteer_id] = {
        "volunteer_name": volunteer_name,
        "team": team,
        "max_shifts": int(max_shifts),
        "assignment_rank": int(assignment_rank),
    }

shift_headers = [cell.value for cell in availability_sheet[2][1:]]
availability = {}
for row in iter_non_empty_rows(availability_sheet, 4):
    volunteer_id = row[0]
    availability[volunteer_id] = {
        shift_id
        for shift_id, marker in zip(shift_headers, row[1:])
        if isinstance(marker, str) and marker.strip().upper() == "Y"
    }

role_headers = [cell.value for cell in qualifications_sheet[2][2:]]
qualifications = {}
for row in iter_non_empty_rows(qualifications_sheet, 3):
    volunteer_id = row[0]
    qualifications[volunteer_id] = {
        role
        for role, marker in zip(role_headers, row[2:])
        if isinstance(marker, str) and marker.strip().upper() == "Y"
    }

demand_rows = []
for shift_id, shift_date, zone, role, required_count, _shift_label in iter_non_empty_rows(demand_sheet, 3):
    demand_rows.append(
        {
            "shift_id": shift_id,
            "shift_date": shift_date,
            "zone": zone,
            "role": role,
            "required_count": int(required_count),
        }
    )

assignment_counts = defaultdict(int)
assigned_by_shift = defaultdict(set)
assignment_rows = []
summary_rows = []

for demand in demand_rows:
    assigned_count = 0
    for slot_number in range(1, demand["required_count"] + 1):
        candidates = []
        for volunteer_id, volunteer in roster.items():
            if volunteer_id not in availability or volunteer_id not in qualifications:
                continue
            if demand["shift_id"] not in availability[volunteer_id]:
                continue
            if demand["role"] not in qualifications[volunteer_id]:
                continue
            if assignment_counts[volunteer_id] >= volunteer["max_shifts"]:
                continue
            if volunteer_id in assigned_by_shift[demand["shift_id"]]:
                continue
            candidates.append(
                (
                    assignment_counts[volunteer_id],
                    volunteer["assignment_rank"],
                    volunteer_id,
                )
            )

        if not candidates:
            continue

        _, _, volunteer_id = min(candidates)
        volunteer = roster[volunteer_id]
        assignment_counts[volunteer_id] += 1
        assigned_by_shift[demand["shift_id"]].add(volunteer_id)
        assigned_count += 1
        assignment_rows.append(
            (
                demand["shift_id"],
                demand["shift_date"],
                demand["zone"],
                demand["role"],
                slot_number,
                volunteer_id,
                volunteer["volunteer_name"],
                volunteer["team"],
            )
        )

    gap_count = demand["required_count"] - assigned_count
    summary_rows.append(
        (
            demand["shift_id"],
            demand["shift_date"],
            demand["zone"],
            demand["role"],
            demand["required_count"],
            assigned_count,
            gap_count,
            "Covered" if gap_count == 0 else "Understaffed",
        )
    )

for row in assignment_rows:
    assignments_sheet.append(row)

for row in summary_rows:
    summary_sheet.append(row)

workbook.save(OUTPUT_PATH)
PY
