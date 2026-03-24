#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict

DATA_DIR = "/app/data"
OUT_DIR = "/app/output"
os.makedirs(OUT_DIR, exist_ok=True)

ROUTES_PATH = os.path.join(DATA_DIR, "board_routes.txt")
WINDOWS_PATH = os.path.join(DATA_DIR, "calibration_windows.csv")
POLICY_PATH = os.path.join(DATA_DIR, "repair_policy.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_plan.json")
OUTPUT_PATH = os.path.join(OUT_DIR, "pcb_repair_plan.json")

SHIFT_TRIGGER = 6


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_routes(path):
    tokens = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                tokens.extend(stripped.split())
    it = iter(tokens)
    lots = int(next(it))
    lines = int(next(it))
    routes = []
    for _ in range(lots):
        stage_count = int(next(it))
        stages = []
        for _ in range(stage_count):
            option_count = int(next(it))
            options = []
            for _ in range(option_count):
                line_id = int(next(it))
                duration = int(next(it))
                options.append((line_id, duration))
            stages.append(options)
        routes.append(stages)
    return lots, lines, routes


def load_windows(path):
    windows = defaultdict(list)
    for row in load_csv(path):
        line_id = int(row["line"])
        windows[line_id].append((int(row["start"]), int(row["end"])))
    for line_id in windows:
        windows[line_id].sort()
    return windows


def normalize_plan(raw):
    plan = []
    for row in raw["line_plan"]:
        plan.append(
            {
                "lot": int(row["lot"]),
                "stage": int(row["stage"]),
                "line": int(row["line"]),
                "start": int(row["start"]),
                "finish": int(row["finish"]),
                "duration": int(row["duration"]),
            }
        )
    return plan


def plan_map(plan):
    return {(row["lot"], row["stage"]): row for row in plan}


def precedence_order(plan):
    base = plan_map(plan)
    base_index = {(row["lot"], row["stage"]): idx for idx, row in enumerate(plan)}
    keys = [(row["lot"], row["stage"]) for row in plan]
    keys.sort(key=lambda key: (key[1], base[key]["start"], base_index[key]))
    return keys


def overlap(a, b, c, d):
    return a < d and c < b


def has_conflict(line_id, start, finish, line_intervals, windows):
    for left, right in line_intervals.get(line_id, []):
        if overlap(start, finish, left, right):
            return True
    for left, right in windows.get(line_id, []):
        if overlap(start, finish, left, right):
            return True
    return False


def earliest_feasible(line_id, anchor, duration, line_intervals, windows):
    start = int(anchor)
    while has_conflict(line_id, start, start + duration, line_intervals, windows):
        start += 1
    return start


def parse_policy(path):
    policy = load_json(path)
    budget = policy.get("change_budget", {})
    freeze = policy.get("freeze", {})
    guards = policy.get("guards", {})
    return {
        "max_machine_changes": int(budget.get("max_machine_changes", 10**9)),
        "max_total_start_shift": int(budget.get("max_total_start_shift_L1", 10**18)),
        "freeze_until": int(freeze["until"]) if freeze.get("until") is not None else None,
        "freeze_fields": [str(x) for x in freeze.get("fields", [])],
        "max_completion_time": int(guards["max_completion_time"]) if guards.get("max_completion_time") is not None else None,
    }


lot_count, _, routes = parse_routes(ROUTES_PATH)
windows = load_windows(WINDOWS_PATH)
policy = parse_policy(POLICY_PATH)
baseline = normalize_plan(load_json(BASELINE_PATH))
baseline_by_key = plan_map(baseline)
order = precedence_order(baseline)

line_intervals = defaultdict(list)
lot_finish = defaultdict(int)
patched = []

line_changes = 0
total_start_shift = 0

for key in order:
    lot, stage = key
    baseline_row = baseline_by_key[key]
    allowed = {line_id: duration for line_id, duration in routes[lot][stage]}

    base_line = baseline_row["line"]
    if base_line not in allowed:
        base_line = min(allowed, key=lambda candidate: allowed[candidate])
    base_duration = allowed[base_line]
    base_start = baseline_row["start"]

    freeze_until = policy["freeze_until"]
    freeze_fields = policy["freeze_fields"]
    frozen = freeze_until is not None and base_start < freeze_until
    force_line = frozen and "line" in freeze_fields
    force_start = frozen and "start" in freeze_fields

    anchor = max(base_start, lot_finish[lot])

    baseline_start = earliest_feasible(
        base_line,
        max(anchor, base_start) if force_start else anchor,
        base_duration,
        line_intervals,
        windows,
    )
    best = {
        "line": base_line,
        "duration": base_duration,
        "start": baseline_start,
    }

    baseline_shift = abs(baseline_start - base_start)
    can_try_alternates = (not force_line) and baseline_shift >= SHIFT_TRIGGER and line_changes < policy["max_machine_changes"]

    if can_try_alternates:
        for line_id, duration in allowed.items():
            change = int(line_id != baseline_row["line"])
            if change and line_changes >= policy["max_machine_changes"]:
                continue
            start = earliest_feasible(line_id, anchor, duration, line_intervals, windows)
            shift = abs(start - base_start)
            score = (shift, change, start + duration, start, line_id)
            best_score = (
                abs(best["start"] - base_start),
                int(best["line"] != baseline_row["line"]),
                best["start"] + best["duration"],
                best["start"],
                best["line"],
            )
            if score < best_score:
                best = {"line": line_id, "duration": duration, "start": start}

    finish = best["start"] + best["duration"]
    next_line_changes = line_changes + int(best["line"] != baseline_row["line"])
    next_total_shift = total_start_shift + abs(best["start"] - base_start)

    line_changes = next_line_changes
    total_start_shift = next_total_shift
    line_intervals[best["line"]].append((best["start"], finish))
    line_intervals[best["line"]].sort()
    lot_finish[lot] = finish

    patched.append(
        {
            "lot": lot,
            "stage": stage,
            "line": best["line"],
            "start": best["start"],
            "finish": finish,
            "duration": best["duration"],
        }
    )

patched.sort(key=lambda row: (row["start"], row["lot"], row["stage"]))
completion_time = max(row["finish"] for row in patched)

if policy["max_completion_time"] is not None and completion_time > policy["max_completion_time"]:
    raise SystemExit("completion_time exceeds guard")
if line_changes > policy["max_machine_changes"]:
    raise SystemExit("line change budget exceeded")
if total_start_shift > policy["max_total_start_shift"]:
    raise SystemExit("start shift budget exceeded")

output = {
    "status": "REPAIRED",
    "completion_time": completion_time,
    "change_budget_usage": {
        "line_changes": line_changes,
        "total_start_shift": total_start_shift,
    },
    "line_plan": patched,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
PY
