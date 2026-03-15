#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA = os.path.join(APP_ROOT, "data")
OUT = os.path.join(APP_ROOT, "output")
os.makedirs(OUT, exist_ok=True)

INSTANCE_PATH = os.path.join(DATA, "cnc_instance.txt")
DOWNTIME_PATH = os.path.join(DATA, "maintenance_windows.csv")
POLICY_PATH = os.path.join(DATA, "recovery_policy.json")
BASELINE_PATH = os.path.join(DATA, "baseline_cnc_plan.json")

PLAN_JSON = os.path.join(OUT, "cnc_recovery_plan.json")
PLAN_CSV = os.path.join(OUT, "cnc_recovery_plan.csv")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_instance(path: str) -> Tuple[int, int, List[List[List[Tuple[int, int]]]]]:
    tokens: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            tokens.extend(s.split())

    it = iter(tokens)
    jobs_n = int(next(it))
    machines_n = int(next(it))
    jobs: List[List[List[Tuple[int, int]]]] = []
    for _ in range(jobs_n):
        ops_n = int(next(it))
        ops: List[List[Tuple[int, int]]] = []
        for _ in range(ops_n):
            choice_n = int(next(it))
            choices: List[Tuple[int, int]] = []
            for _ in range(choice_n):
                machine = int(next(it))
                dur = int(next(it))
                choices.append((machine, dur))
            ops.append(choices)
        jobs.append(ops)
    return jobs_n, machines_n, jobs


def load_downtime(path: str) -> Dict[int, List[Tuple[int, int]]]:
    downtime: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    for row in load_csv(path):
        machine = int(row["machine"])
        start = int(row["start"])
        end = int(row["end"])
        downtime[machine].append((start, end))
    for machine in downtime:
        downtime[machine].sort()
    return downtime


def normalize_schedule(rows: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    schedule: List[Dict[str, int]] = []
    for row in rows:
        schedule.append({
            "job": int(row["job"]),
            "op": int(row["op"]),
            "machine": int(row["machine"]),
            "start": int(row["start"]),
            "end": int(row["end"]),
            "dur": int(row["dur"]),
        })
    return schedule


def schedule_map(schedule: List[Dict[str, int]]) -> Dict[Tuple[int, int], Dict[str, int]]:
    return {(row["job"], row["op"]): row for row in schedule}


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a < d and c < b


def has_conflict(
    machine: int,
    start: int,
    end: int,
    machine_intervals: Dict[int, List[Tuple[int, int]]],
    downtime: Dict[int, List[Tuple[int, int]]],
) -> bool:
    for a, b in machine_intervals.get(machine, []):
        if overlap(start, end, a, b):
            return True
    for a, b in downtime.get(machine, []):
        if overlap(start, end, a, b):
            return True
    return False


def earliest_feasible_time(
    machine: int,
    anchor: int,
    dur: int,
    machine_intervals: Dict[int, List[Tuple[int, int]]],
    downtime: Dict[int, List[Tuple[int, int]]],
    safety: int = 200000,
) -> int:
    t = max(0, int(anchor))
    for _ in range(safety):
        if not has_conflict(machine, t, t + dur, machine_intervals, downtime):
            return t
        t += 1
    return t


def precedence_aware_order(baseline: List[Dict[str, int]]) -> List[Tuple[int, int]]:
    base_map = schedule_map(baseline)
    base_index = {(row["job"], row["op"]): idx for idx, row in enumerate(baseline)}
    keys = list(base_map.keys())
    keys.sort(key=lambda key: (key[1], base_map[key]["start"], base_index[key]))
    return keys


def parse_policy(path: str) -> Tuple[int, List[str], int, int]:
    policy = load_json(path)
    freeze = {}
    if isinstance(policy.get("freeze_window"), dict):
        freeze = policy["freeze_window"]
    elif isinstance(policy.get("freeze"), dict):
        freeze = policy["freeze"]

    freeze_until = int(
        freeze.get("freeze_until", freeze.get("until", policy.get("freeze_until", 0)))
    )

    locked_fields_raw = (
        freeze.get("locked_fields")
        or freeze.get("lock_fields")
        or freeze.get("freeze_fields")
        or freeze.get("fields")
        or policy.get("locked_fields")
        or policy.get("lock_fields")
        or policy.get("freeze_fields")
        or policy.get("fields")
        or []
    )
    locked_fields = [str(field) for field in locked_fields_raw]

    budget = policy.get("change_budget", {})
    max_machine_changes = int(budget.get("max_machine_changes", 10**9))
    max_total_start_shift = int(budget.get("max_total_start_shift_L1", 10**18))
    return freeze_until, locked_fields, max_machine_changes, max_total_start_shift


jobs_n, machines_n, jobs = parse_instance(INSTANCE_PATH)
downtime = load_downtime(DOWNTIME_PATH)
baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
base_map = schedule_map(baseline)
order = precedence_aware_order(baseline)

freeze_until, locked_fields, max_machine_changes, max_total_start_shift = parse_policy(POLICY_PATH)

machine_intervals: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
job_end: Dict[int, int] = defaultdict(int)
patched: List[Dict[str, int]] = []
machine_changes = 0
total_start_shift = 0


def allowed_map(job: int, op: int) -> Dict[int, int]:
    return {int(machine): int(dur) for machine, dur in jobs[job][op]}


for key in order:
    job, op = key
    baseline_row = base_map[key]
    allowed = allowed_map(job, op)

    baseline_machine_original = int(baseline_row["machine"])
    baseline_machine = baseline_machine_original
    if baseline_machine not in allowed:
        baseline_machine = min(allowed, key=lambda machine: (allowed[machine], machine))

    baseline_start = int(baseline_row["start"])
    frozen = baseline_start < freeze_until

    force_machine = frozen and "machine" in locked_fields
    force_start = frozen and "start" in locked_fields
    force_end = frozen and "end" in locked_fields

    anchor = max(baseline_start, job_end[job])

    candidates: List[Tuple[int, int, int]] = []
    if force_machine:
        if baseline_machine not in allowed:
            raise RuntimeError(f"Frozen baseline machine is illegal for {key}")
        candidates = [(baseline_machine, allowed[baseline_machine], 0)]
    else:
        candidates.append((baseline_machine, allowed[baseline_machine], int(baseline_machine != baseline_machine_original)))
        for machine, dur in sorted(allowed.items()):
            if machine == baseline_machine:
                continue
            candidates.append((machine, dur, int(machine != baseline_machine_original)))

    best: Optional[Tuple[Tuple[int, int, int, int], int, int, int, int]] = None
    for machine, dur, machine_change_flag in candidates:
        projected_machine_changes = machine_changes + machine_change_flag
        if projected_machine_changes > max_machine_changes:
            continue

        if force_start:
            start = int(baseline_row["start"])
            if start < anchor:
                continue
            if has_conflict(machine, start, start + dur, machine_intervals, downtime):
                continue
        else:
            start = earliest_feasible_time(machine, anchor, dur, machine_intervals, downtime)

        end = start + dur
        if force_end and end != int(baseline_row["end"]):
            continue

        projected_total_shift = total_start_shift + abs(start - baseline_start)
        if projected_total_shift > max_total_start_shift:
            continue

        score = (
            machine_change_flag,
            abs(start - baseline_start),
            end,
            machine,
        )
        if best is None or score < best[0]:
            best = (score, start, end, machine, dur)

    if best is None:
        raise RuntimeError(f"No feasible repair candidate for operation {key}")

    _, start, end, machine, dur = best
    machine_changes += int(machine != baseline_machine_original)
    total_start_shift += abs(start - baseline_start)
    machine_intervals[machine].append((start, end))
    machine_intervals[machine].sort()
    job_end[job] = end
    patched.append({
        "job": job,
        "op": op,
        "machine": machine,
        "start": start,
        "end": end,
        "dur": dur,
    })

patched.sort(key=lambda row: (row["start"], row["job"], row["op"]))
makespan = max((row["end"] for row in patched), default=0)

payload = {
    "status": "FEASIBLE",
    "makespan": int(makespan),
    "machine_changes": int(machine_changes),
    "total_start_shift": int(total_start_shift),
    "schedule": patched,
}

with open(PLAN_JSON, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

with open(PLAN_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["job", "op", "machine", "start", "end", "dur"])
    writer.writeheader()
    for row in patched:
        writer.writerow(row)
PY
