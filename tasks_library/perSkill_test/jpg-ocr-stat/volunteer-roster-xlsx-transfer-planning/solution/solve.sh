#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font


WORKSPACE = Path("/app/workspace")
VOLUNTEERS_PATH = WORKSPACE / "data" / "volunteers.tsv"
SHIFTS_PATH = WORKSPACE / "data" / "shift_needs.csv"
AVAILABILITY_PATH = WORKSPACE / "data" / "availability.json"
OUTPUT_PATH = WORKSPACE / "volunteer_shift_plan.xlsx"


@dataclass
class Volunteer:
    volunteer_id: str
    volunteer_name: str
    team: str
    eligible_roles: list[str]
    max_shifts: int
    order: int


@dataclass
class Shift:
    shift_id: str
    shift_date: date
    start_time: time
    end_time: time
    site: str
    role: str
    required_count: int
    order: int


def read_volunteers(path: Path) -> list[Volunteer]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        volunteers: list[Volunteer] = []
        for index, row in enumerate(reader):
            volunteers.append(
                Volunteer(
                    volunteer_id=row["volunteer_id"],
                    volunteer_name=row["volunteer_name"],
                    team=row["team"],
                    eligible_roles=row["eligible_roles"].split("|"),
                    max_shifts=int(row["max_shifts"]),
                    order=index,
                )
            )
        return volunteers


def read_shifts(path: Path) -> list[Shift]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        shifts: list[Shift] = []
        for index, row in enumerate(reader):
            shifts.append(
                Shift(
                    shift_id=row["shift_id"],
                    shift_date=datetime.strptime(row["shift_date"], "%Y-%m-%d").date(),
                    start_time=datetime.strptime(row["start_time"], "%H:%M").time(),
                    end_time=datetime.strptime(row["end_time"], "%H:%M").time(),
                    site=row["site"],
                    role=row["role"],
                    required_count=int(row["required_count"]),
                    order=index,
                )
            )
        return shifts


def read_availability(path: Path) -> dict[str, set[str]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {
        entry["volunteer_id"]: set(entry["available_shifts"])
        for entry in payload["availability"]
    }


def overlaps(a: Shift, b: Shift) -> bool:
    if a.shift_date != b.shift_date:
        return False
    return a.start_time < b.end_time and a.end_time > b.start_time


volunteers = read_volunteers(VOLUNTEERS_PATH)
shifts = read_shifts(SHIFTS_PATH)
availability = read_availability(AVAILABILITY_PATH)

assigned_shifts_by_volunteer: dict[str, list[Shift]] = {volunteer.volunteer_id: [] for volunteer in volunteers}
assignments: list[dict[str, object]] = []

for shift in shifts:
    candidates: list[Volunteer] = []
    for volunteer in volunteers:
        if shift.shift_id not in availability.get(volunteer.volunteer_id, set()):
            continue
        if shift.role not in volunteer.eligible_roles:
            continue
        if len(assigned_shifts_by_volunteer[volunteer.volunteer_id]) >= volunteer.max_shifts:
            continue
        if any(overlaps(shift, assigned_shift) for assigned_shift in assigned_shifts_by_volunteer[volunteer.volunteer_id]):
            continue
        candidates.append(volunteer)

    candidates.sort(key=lambda volunteer: (len(assigned_shifts_by_volunteer[volunteer.volunteer_id]), volunteer.order))
    selected = candidates[: shift.required_count]

    for volunteer in selected:
        assigned_shifts_by_volunteer[volunteer.volunteer_id].append(shift)
        assignments.append({"shift": shift, "volunteer": volunteer})

workbook = Workbook()
default_sheet = workbook.active
workbook.remove(default_sheet)

needs_sheet = workbook.create_sheet("班次需求")
assign_sheet = workbook.create_sheet("分配结果")
load_sheet = workbook.create_sheet("人员负载")
summary_sheet = workbook.create_sheet("缺口概览")


def style_header(sheet, headers: list[str]) -> None:
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)


style_header(
    needs_sheet,
    [
        "shift_id",
        "shift_date",
        "start_time",
        "end_time",
        "site",
        "role",
        "required_count",
        "assigned_count",
        "gap_count",
    ],
)

for row_index, shift in enumerate(shifts, start=2):
    needs_sheet[f"A{row_index}"] = shift.shift_id
    needs_sheet[f"B{row_index}"] = shift.shift_date
    needs_sheet[f"C{row_index}"] = shift.start_time
    needs_sheet[f"D{row_index}"] = shift.end_time
    needs_sheet[f"E{row_index}"] = shift.site
    needs_sheet[f"F{row_index}"] = shift.role
    needs_sheet[f"G{row_index}"] = shift.required_count
    needs_sheet[f"H{row_index}"] = f'=COUNTIF(分配结果!$A:$A,A{row_index})'
    needs_sheet[f"I{row_index}"] = f'=MAX(G{row_index}-H{row_index},0)'

style_header(
    assign_sheet,
    [
        "shift_id",
        "shift_date",
        "start_time",
        "end_time",
        "site",
        "role",
        "volunteer_id",
        "volunteer_name",
        "team",
        "load_after_assignment",
        "overlap_flag",
    ],
)

for row_index, assignment in enumerate(assignments, start=2):
    shift = assignment["shift"]
    volunteer = assignment["volunteer"]
    assign_sheet[f"A{row_index}"] = shift.shift_id
    assign_sheet[f"B{row_index}"] = shift.shift_date
    assign_sheet[f"C{row_index}"] = shift.start_time
    assign_sheet[f"D{row_index}"] = shift.end_time
    assign_sheet[f"E{row_index}"] = shift.site
    assign_sheet[f"F{row_index}"] = shift.role
    assign_sheet[f"G{row_index}"] = volunteer.volunteer_id
    assign_sheet[f"H{row_index}"] = volunteer.volunteer_name
    assign_sheet[f"I{row_index}"] = volunteer.team
    assign_sheet[f"J{row_index}"] = f'=COUNTIF($G$2:G{row_index},G{row_index})'
    assign_sheet[f"K{row_index}"] = (
        f'=IF(COUNTIFS($G:$G,G{row_index},$B:$B,B{row_index},$C:$C,"<"&D{row_index},$D:$D,">"&C{row_index})>1,"冲突","")'
    )

style_header(
    load_sheet,
    [
        "volunteer_id",
        "volunteer_name",
        "team",
        "max_shifts",
        "assigned_shifts",
        "remaining_capacity",
        "conflict_flag",
    ],
)

for row_index, volunteer in enumerate(volunteers, start=2):
    load_sheet[f"A{row_index}"] = volunteer.volunteer_id
    load_sheet[f"B{row_index}"] = volunteer.volunteer_name
    load_sheet[f"C{row_index}"] = volunteer.team
    load_sheet[f"D{row_index}"] = volunteer.max_shifts
    load_sheet[f"E{row_index}"] = f'=COUNTIF(分配结果!$G:$G,A{row_index})'
    load_sheet[f"F{row_index}"] = f'=D{row_index}-E{row_index}'
    load_sheet[f"G{row_index}"] = f'=IF(COUNTIFS(分配结果!$G:$G,A{row_index},分配结果!$K:$K,"冲突")>0,"冲突","")'

style_header(summary_sheet, ["metric", "value"])
needs_last_row = len(shifts) + 1
assign_last_row = len(assignments) + 1
load_last_row = len(volunteers) + 1
metrics = [
    ("total_required", f"=SUM(班次需求!$G$2:$G${needs_last_row})"),
    ("total_assigned", '=MAX(COUNTA(分配结果!$A:$A)-1,0)'),
    ("total_gap", f"=SUM(班次需求!$I$2:$I${needs_last_row})"),
    ("filled_shift_count", f'=COUNTIF(班次需求!$I$2:$I${needs_last_row},0)'),
    ("unfilled_shift_count", f'=COUNTIF(班次需求!$I$2:$I${needs_last_row},">0")'),
    ("volunteers_used", f'=COUNTIF(人员负载!$E$2:$E${load_last_row},">0")'),
    ("conflicted_assignment_rows", f'=COUNTIF(分配结果!$K$2:$K${assign_last_row},"冲突")'),
]

for row_index, (metric, formula) in enumerate(metrics, start=2):
    summary_sheet[f"A{row_index}"] = metric
    summary_sheet[f"B{row_index}"] = formula

for sheet in (needs_sheet, assign_sheet, load_sheet, summary_sheet):
    sheet.freeze_panes = "A2"

for row in range(2, needs_sheet.max_row + 1):
    needs_sheet[f"B{row}"].number_format = "yyyy-mm-dd"
    needs_sheet[f"C{row}"].number_format = "hh:mm"
    needs_sheet[f"D{row}"].number_format = "hh:mm"

for row in range(2, assign_sheet.max_row + 1):
    assign_sheet[f"B{row}"].number_format = "yyyy-mm-dd"
    assign_sheet[f"C{row}"].number_format = "hh:mm"
    assign_sheet[f"D{row}"].number_format = "hh:mm"

column_widths = {
    "班次需求": {"A": 12, "B": 12, "C": 10, "D": 10, "E": 16, "F": 14, "G": 14, "H": 14, "I": 12},
    "分配结果": {"A": 12, "B": 12, "C": 10, "D": 10, "E": 16, "F": 14, "G": 14, "H": 14, "I": 14, "J": 20, "K": 14},
    "人员负载": {"A": 14, "B": 14, "C": 14, "D": 12, "E": 16, "F": 18, "G": 14},
    "缺口概览": {"A": 28, "B": 12},
}

for sheet_name, widths in column_widths.items():
    sheet = workbook[sheet_name]
    for column_name, width in widths.items():
        sheet.column_dimensions[column_name].width = width

workbook.save(OUTPUT_PATH)
PY

python3 /root/.codex/skills/xlsx/recalc.py /app/workspace/volunteer_shift_plan.xlsx 90
