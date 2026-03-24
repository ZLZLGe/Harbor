#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
DATA_DIR="${DATA_DIR:-$APP_ROOT/data}"
OUT_DIR="${OUT_DIR:-$APP_ROOT/output}"
mkdir -p "$OUT_DIR"

python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict

APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA_DIR = os.environ.get("DATA_DIR", f"{APP_ROOT}/data")
OUT_DIR = os.environ.get("OUT_DIR", f"{APP_ROOT}/output")

ROUTES_PATH = os.path.join(DATA_DIR, "tray_routes.json")
DOWNTIME_PATH = os.path.join(DATA_DIR, "unit_downtime.csv")
POLICY_PATH = os.path.join(DATA_DIR, "repair_policy.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_cssd_plan.json")
OUTPUT_PATH = os.path.join(OUT_DIR, "cssd_day_plan.json")

THRESHOLD = 6


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def overlap(a, b, c, d):
    return a < d and c < b


def load_routes():
    raw = load_json(ROUTES_PATH)
    units = {int(row["unit_id"]): str(row["unit_name"]) for row in raw["units"]}
    trays = raw["trays"]
    return units, trays


def load_downtime():
    windows = defaultdict(list)
    for row in load_csv(DOWNTIME_PATH):
        unit_id = int(row["unit_id"])
        windows[unit_id].append((int(row["start"]), int(row["end"])))
    for unit_id in windows:
        windows[unit_id].sort()
    return windows


def schedule_map(rows):
    return {(row["tray_id"], int(row["step_index"])): row for row in rows}


def precedence_aware_order(rows):
    indexed = {(row["tray_id"], int(row["step_index"])): idx for idx, row in enumerate(rows)}
    mapped = schedule_map(rows)
    keys = list(mapped)
    keys.sort(key=lambda key: (key[1], int(mapped[key]["start"]), indexed[key]))
    return keys


def has_conflict(unit_id, start, finish, unit_intervals, downtime):
    for left, right in unit_intervals.get(unit_id, []):
        if overlap(start, finish, left, right):
            return True
    for left, right in downtime.get(unit_id, []):
        if overlap(start, finish, left, right):
            return True
    return False


def earliest_feasible_time(unit_id, anchor, duration, unit_intervals, downtime, safety=200000):
    t = int(anchor)
    for _ in range(safety):
        if not has_conflict(unit_id, t, t + duration, unit_intervals, downtime):
            return t
        t += 1
    return t


def insert_interval(unit_intervals, unit_id, start, finish):
    unit_intervals[unit_id].append((start, finish))
    unit_intervals[unit_id].sort()


units, trays = load_routes()
downtime = load_downtime()
policy = load_json(POLICY_PATH)
baseline = load_json(BASELINE_PATH)["tray_plan"]
baseline_map = schedule_map(baseline)
order = precedence_aware_order(baseline)
tray_index = {tray["tray_id"]: tray for tray in trays}

freeze = policy.get("freeze", {})
freeze_until = freeze.get("until")
freeze_fields = [str(field) for field in freeze.get("fields", [])]
budget = policy.get("change_budget", {})
max_unit_changes = int(budget.get("max_machine_changes", 10**9))
max_total_shift = int(budget.get("max_total_start_shift_L1", 10**18))

unit_intervals = defaultdict(list)
tray_ready = defaultdict(int)
patched = []
unit_changes = 0
total_start_shift = 0

for tray_id, step_index in order:
    base_row = baseline_map[(tray_id, step_index)]
    tray = tray_index[tray_id]
    step = tray["steps"][step_index]
    allowed = {int(opt["unit_id"]): int(opt["duration"]) for opt in step["options"]}

    base_unit = int(base_row["unit_id"])
    if base_unit not in allowed:
        base_unit = min(allowed, key=allowed.get)
    base_duration = allowed[base_unit]
    base_start = int(base_row["start"])

    frozen = freeze_until is not None and base_start < int(freeze_until)
    anchor = max(base_start, tray_ready[tray_id])

    forced_unit = base_unit if frozen and "unit_id" in freeze_fields else None
    forced_start = base_start if frozen and "start" in freeze_fields else None

    def best_candidate(candidate_units):
        best = None
        for unit_id in candidate_units:
            duration = allowed[unit_id]
            change_cost = int(unit_id != int(base_row["unit_id"]))
            if change_cost == 1 and unit_changes >= max_unit_changes:
                continue
            candidate_anchor = anchor if forced_start is None else max(anchor, forced_start)
            start = earliest_feasible_time(unit_id, candidate_anchor, duration, unit_intervals, downtime)
            score = (abs(start - base_start), start, unit_id)
            if best is None or score < best[0]:
                best = (score, start, start + duration, unit_id, duration, change_cost)
        return best

    if forced_unit is not None:
        chosen = best_candidate([forced_unit])
    else:
        chosen = best_candidate([base_unit])
        if chosen[1] - base_start >= THRESHOLD and unit_changes < max_unit_changes:
            alternate = best_candidate(sorted(allowed))
            if alternate is not None and alternate[1] < chosen[1]:
                chosen = alternate

    _, start, finish, unit_id, duration, change_cost = chosen
    insert_interval(unit_intervals, unit_id, start, finish)
    tray_ready[tray_id] = finish
    unit_changes += change_cost
    total_start_shift += abs(start - base_start)

    patched.append(
        {
            "tray_id": tray_id,
            "step": str(step["step"]),
            "step_index": step_index,
            "unit_id": unit_id,
            "unit_name": units[unit_id],
            "start": start,
            "finish": finish,
            "duration": duration,
        }
    )

if unit_changes > max_unit_changes or total_start_shift > max_total_shift:
    raise RuntimeError("Repair result exceeded change budget")

ready_order = sorted(
    ((tray_id, finish) for tray_id, finish in tray_ready.items()),
    key=lambda item: (item[1], item[0]),
)

result = {
    "status": "DAY_PLAN_READY",
    "last_ready_minute": max((row["finish"] for row in patched), default=0),
    "budget_usage": {
        "unit_changes": unit_changes,
        "total_start_shift": total_start_shift,
    },
    "ready_trays": [tray_id for tray_id, _ in ready_order],
    "tray_plan": patched,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
