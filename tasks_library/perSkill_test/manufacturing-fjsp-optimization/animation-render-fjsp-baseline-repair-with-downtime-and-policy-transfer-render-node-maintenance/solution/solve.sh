#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUT_DIR="${OUT_DIR:-/app/output}"

DATA_DIR="$DATA_DIR" OUT_DIR="$OUT_DIR" python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict

DATA_DIR = os.environ["DATA_DIR"]
OUT_DIR = os.environ["OUT_DIR"]

MANIFEST_PATH = f"{DATA_DIR}/show_manifest.json"
WINDOWS_PATH = f"{DATA_DIR}/maintenance_windows.csv"
POLICY_PATH = f"{DATA_DIR}/recovery_policy.json"
BASELINE_PATH = f"{DATA_DIR}/baseline_render_queue.csv"
OUTPUT_PATH = f"{OUT_DIR}/render_recovery_plan.json"

os.makedirs(OUT_DIR, exist_ok=True)


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
baseline = []
for row in load_csv(BASELINE_PATH):
    baseline.append(
        {
            "shot_id": str(row["shot_id"]),
            "stage": str(row["stage"]),
            "stage_index": int(row["stage_index"]),
            "station_id": str(row["station_id"]),
            "station_name": str(row["station_name"]),
            "start": int(row["start"]),
            "finish": int(row["finish"]),
            "duration": int(row["duration"]),
        }
    )

station_names = {
    str(row["station_id"]): str(row["station_name"])
    for row in manifest["stations"]
}
shots = {
    str(row["shot_id"]): row
    for row in manifest["shots"]
}
windows = defaultdict(list)
for row in load_csv(WINDOWS_PATH):
    windows[str(row["station_id"])].append((int(row["start"]), int(row["end"])))
for station_id in windows:
    windows[station_id].sort()

freeze_before = int(policy["freeze"]["before_minute"])
freeze_fields = set(policy["freeze"]["fields"])
max_changes = int(policy["change_budget"]["max_station_changes"])
max_total_shift = int(policy["change_budget"]["max_total_start_shift"])

baseline_map = {
    (row["shot_id"], row["stage_index"]): row
    for row in baseline
}
baseline_index = {
    (row["shot_id"], row["stage_index"]): idx
    for idx, row in enumerate(baseline)
}
order = sorted(
    baseline_map,
    key=lambda key: (
        key[1],
        baseline_map[key]["start"],
        baseline_index[key],
    ),
)


def allowed_options(shot_id, stage_index):
    stage = shots[shot_id]["stages"][stage_index]
    return {
        str(option["station_id"]): int(option["duration"])
        for option in stage["options"]
    }, str(stage["stage"])


def has_conflict(station_id, start, finish, station_intervals):
    for left, right in station_intervals.get(station_id, []):
        if overlap(start, finish, left, right):
            return True
    for left, right in windows.get(station_id, []):
        if overlap(start, finish, left, right):
            return True
    return False


def earliest_feasible(station_id, start_at, duration, station_intervals):
    minute = int(start_at)
    while has_conflict(station_id, minute, minute + duration, station_intervals):
        minute += 1
    return minute


station_intervals = defaultdict(list)
shot_finish = defaultdict(int)
plan = []
station_changes = 0
total_start_shift = 0

for key in order:
    shot_id, stage_index = key
    baseline_row = baseline_map[key]
    allowed, stage_name = allowed_options(shot_id, stage_index)
    anchor = max(baseline_row["start"], shot_finish[shot_id])
    frozen = baseline_row["start"] < freeze_before
    candidates = []

    base_station = baseline_row["station_id"]
    candidates.append((base_station, allowed[base_station], 0))
    for station_id, duration in allowed.items():
        if station_id != base_station:
            candidates.append((station_id, duration, 1))

    best = None
    for station_id, duration, change_flag in candidates:
        if change_flag == 1 and station_changes >= max_changes:
            continue
        if frozen and "station_id" in freeze_fields and station_id != base_station:
            continue

        if frozen and "start" in freeze_fields:
            start = baseline_row["start"]
            if start < anchor:
                continue
            if has_conflict(station_id, start, start + duration, station_intervals):
                continue
        else:
            start = earliest_feasible(station_id, anchor, duration, station_intervals)

        finish = start + duration
        start_shift = abs(start - baseline_row["start"])
        projected_shift = total_start_shift + start_shift
        projected_changes = station_changes + change_flag
        if projected_shift > max_total_shift:
            continue
        if projected_changes > max_changes:
            continue

        score = (start_shift, change_flag, finish, start)
        if best is None or score < best[0]:
            best = (score, station_id, duration, start, finish, start_shift, change_flag)

    if best is None:
        raise RuntimeError(f"no feasible repair candidate for {shot_id} stage {stage_index}")

    _, station_id, duration, start, finish, start_shift, change_flag = best
    station_intervals[station_id].append((start, finish))
    station_intervals[station_id].sort()
    shot_finish[shot_id] = finish
    station_changes += change_flag
    total_start_shift += start_shift
    plan.append(
        {
            "shot_id": shot_id,
            "stage": stage_name,
            "stage_index": stage_index,
            "station_id": station_id,
            "station_name": station_names[station_id],
            "start": start,
            "finish": finish,
            "duration": duration,
        }
    )

review_finish = {
    row["shot_id"]: row["finish"]
    for row in plan
    if row["stage_index"] == 3
}
payload = {
    "status": "READY_FOR_REVIEW",
    "last_review_minute": max((row["finish"] for row in plan), default=0),
    "budget_usage": {
        "station_changes": station_changes,
        "total_start_shift": total_start_shift,
    },
    "review_queue": [
        shot_id
        for shot_id, _ in sorted(review_finish.items(), key=lambda item: (item[1], item[0]))
    ],
    "render_plan": plan,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
