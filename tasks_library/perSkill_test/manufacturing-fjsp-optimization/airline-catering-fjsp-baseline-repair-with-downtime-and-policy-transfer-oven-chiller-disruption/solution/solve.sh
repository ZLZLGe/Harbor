#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
DATA_DIR="${DATA_DIR:-$APP_ROOT/data}"
OUT_DIR="${OUT_DIR:-$APP_ROOT/output}"
mkdir -p "$OUT_DIR"

DATA_DIR="$DATA_DIR" OUT_DIR="$OUT_DIR" python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict

DATA_DIR = os.environ["DATA_DIR"]
OUT_DIR = os.environ["OUT_DIR"]

MANIFEST_PATH = os.path.join(DATA_DIR, "flight_service_manifest.json")
WINDOWS_PATH = os.path.join(DATA_DIR, "equipment_maintenance.csv")
POLICY_PATH = os.path.join(DATA_DIR, "repair_policy.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_catering_plan.json")
OUTPUT_PATH = os.path.join(OUT_DIR, "catering_shift_plan.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def overlap(a, b, c, d):
    return a < d and c < b


manifest = load_json(MANIFEST_PATH)
policy = load_json(POLICY_PATH)
baseline_raw = load_json(BASELINE_PATH)
baseline = baseline_raw["kitchen_plan"]

equipment_meta = {
    str(row["equipment_id"]): {
        "equipment_name": str(row["equipment_name"]),
        "group": str(row["group"]),
    }
    for row in manifest["equipment"]
}
flights = {
    str(row["flight_id"]): row
    for row in manifest["flights"]
}
windows = defaultdict(list)
for row in load_csv(WINDOWS_PATH):
    windows[str(row["equipment_id"])].append((int(row["start"]), int(row["end"])))
for equipment_id in windows:
    windows[equipment_id].sort()

freeze_before = int(policy["freeze"]["before_minute"])
freeze_fields = set(policy["freeze"]["fields"])
max_changes = int(policy["change_budget"]["max_equipment_changes"])
max_total_shift = int(policy["change_budget"]["max_total_start_shift"])

baseline_map = {
    (str(row["flight_id"]), int(row["stage_index"])): row
    for row in baseline
}
baseline_index = {
    (str(row["flight_id"]), int(row["stage_index"])): idx
    for idx, row in enumerate(baseline)
}
order = sorted(
    baseline_map,
    key=lambda key: (
        key[1],
        int(baseline_map[key]["start"]),
        baseline_index[key],
    ),
)


def allowed_options(flight_id, stage_index):
    stage = flights[flight_id]["stages"][stage_index]
    options = {
        str(option["equipment_id"]): int(option["duration"])
        for option in stage["options"]
    }
    return options, str(stage["stage"]), str(stage["group"])


def has_conflict(equipment_id, start, finish, equipment_intervals):
    for left, right in equipment_intervals.get(equipment_id, []):
        if overlap(start, finish, left, right):
            return True
    for left, right in windows.get(equipment_id, []):
        if overlap(start, finish, left, right):
            return True
    return False


def earliest_feasible(equipment_id, anchor, duration, equipment_intervals):
    minute = int(anchor)
    while has_conflict(equipment_id, minute, minute + duration, equipment_intervals):
        minute += 1
    return minute


equipment_intervals = defaultdict(list)
flight_finish = defaultdict(int)
plan = []
equipment_changes = 0
total_start_shift = 0

for key in order:
    flight_id, stage_index = key
    baseline_row = baseline_map[key]
    options, stage_name, equipment_group = allowed_options(flight_id, stage_index)
    anchor = max(int(baseline_row["start"]), flight_finish[flight_id])
    frozen = int(baseline_row["start"]) < freeze_before
    base_equipment = str(baseline_row["equipment_id"])
    candidates = [(base_equipment, options[base_equipment], 0)]
    for equipment_id, duration in options.items():
        if equipment_id != base_equipment:
            candidates.append((equipment_id, duration, 1))

    best = None
    for equipment_id, duration, change_flag in candidates:
        if frozen and "equipment_id" in freeze_fields and equipment_id != base_equipment:
            continue
        if change_flag == 1 and equipment_changes >= max_changes:
            continue

        if frozen and "start" in freeze_fields:
            start = int(baseline_row["start"])
            if start < anchor:
                continue
            if has_conflict(equipment_id, start, start + duration, equipment_intervals):
                continue
        else:
            start = earliest_feasible(equipment_id, anchor, duration, equipment_intervals)

        finish = start + duration
        start_shift = abs(start - int(baseline_row["start"]))
        if total_start_shift + start_shift > max_total_shift:
            continue
        if equipment_changes + change_flag > max_changes:
            continue

        score = (start_shift, change_flag, finish, start, equipment_id)
        if best is None or score < best[0]:
            best = (score, equipment_id, duration, start, finish, start_shift, change_flag, stage_name, equipment_group)

    if best is None:
        raise RuntimeError(f"no feasible repair candidate for {flight_id} stage {stage_index}")

    _, equipment_id, duration, start, finish, start_shift, change_flag, stage_name, equipment_group = best
    equipment_intervals[equipment_id].append((start, finish))
    equipment_intervals[equipment_id].sort()
    flight_finish[flight_id] = finish
    equipment_changes += change_flag
    total_start_shift += start_shift
    plan.append(
        {
            "flight_id": flight_id,
            "stage": stage_name,
            "stage_index": stage_index,
            "equipment_group": equipment_group,
            "equipment_id": equipment_id,
            "equipment_name": equipment_meta[equipment_id]["equipment_name"],
            "start": start,
            "finish": finish,
            "duration": duration,
        }
    )


dispatch_board = []
for flight_id, flight in flights.items():
    ready_minute = max(
        row["finish"]
        for row in plan
        if row["flight_id"] == flight_id and row["stage_index"] == len(flight["stages"]) - 1
    )
    dispatch_board.append(
        {
            "flight_id": flight_id,
            "ready_minute": ready_minute,
            "departure_minute": int(flight["departure_minute"]),
            "buffer_to_departure": int(flight["departure_minute"]) - ready_minute,
        }
    )

dispatch_board.sort(key=lambda row: (row["departure_minute"], row["flight_id"]))

payload = {
    "status": "DISPATCHABLE",
    "last_ready_minute": max((row["finish"] for row in plan), default=0),
    "budget_usage": {
        "equipment_changes": equipment_changes,
        "total_start_shift": total_start_shift,
    },
    "dispatch_board": dispatch_board,
    "kitchen_plan": plan,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
