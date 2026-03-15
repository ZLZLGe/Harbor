#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUT_DIR="${OUT_DIR:-/app/output}"
mkdir -p "${OUT_DIR}"

DATA_DIR="${DATA_DIR}" OUT_DIR="${OUT_DIR}" python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = os.environ["DATA_DIR"]
OUT_DIR = os.environ["OUT_DIR"]

INSTANCE_PATH = os.path.join(DATA_DIR, "instance.txt")
DOWNTIME_PATH = os.path.join(DATA_DIR, "downtime.csv")
POLICY_PATH = os.path.join(DATA_DIR, "policy.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_solution.json")
SOLUTION_PATH = os.path.join(OUT_DIR, "solution.json")
CSV_PATH = os.path.join(OUT_DIR, "schedule.csv")


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
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tokens.extend(line.split())
    it = iter(tokens)
    jobs = int(next(it))
    machines = int(next(it))
    parsed: List[List[List[Tuple[int, int]]]] = []
    for _ in range(jobs):
        n_ops = int(next(it))
        ops: List[List[Tuple[int, int]]] = []
        for _ in range(n_ops):
            k = int(next(it))
            choices: List[Tuple[int, int]] = []
            for _ in range(k):
                choices.append((int(next(it)), int(next(it))))
            ops.append(choices)
        parsed.append(ops)
    return jobs, machines, parsed


def normalize_schedule(rows: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    out: List[Dict[str, int]] = []
    for row in rows:
        out.append(
            {
                "job": int(row["job"]),
                "op": int(row["op"]),
                "machine": int(row["machine"]),
                "start": int(row["start"]),
                "end": int(row["end"]),
                "dur": int(row["dur"]),
            }
        )
    return out


def load_downtime(path: str) -> Dict[int, List[Tuple[int, int]]]:
    out: Dict[int, List[Tuple[int, int]]] = {}
    if not os.path.exists(path):
        return out
    for row in load_csv(path):
        machine = int(row["machine"])
        out.setdefault(machine, []).append((int(row["start"]), int(row["end"])))
    for machine in out:
        out[machine].sort()
    return out


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
    duration: int,
    machine_intervals: Dict[int, List[Tuple[int, int]]],
    downtime: Dict[int, List[Tuple[int, int]]],
) -> int:
    t = int(anchor)
    while True:
        if not has_conflict(machine, t, t + duration, machine_intervals, downtime):
            return t
        t += 1


def schedule_map(schedule: List[Dict[str, int]]) -> Dict[Tuple[int, int], Dict[str, int]]:
    return {(row["job"], row["op"]): row for row in schedule}


def parse_policy(path: str) -> Tuple[int, int, Optional[int], List[str]]:
    policy = load_json(path)
    budget = policy.get("change_budget", {})
    max_machine_changes = int(budget.get("max_machine_changes", 10**9))
    max_start_shift = int(budget.get("max_total_start_shift_L1", 10**18))

    freeze_until = None
    freeze_fields: List[str] = []
    freeze = policy.get("freeze")
    if isinstance(freeze, dict):
        if freeze.get("until") is not None:
            freeze_until = int(freeze["until"])
        elif freeze.get("freeze_until") is not None:
            freeze_until = int(freeze["freeze_until"])
        if isinstance(freeze.get("fields"), list):
            freeze_fields = [str(x) for x in freeze["fields"]]
        elif isinstance(freeze.get("freeze_fields"), list):
            freeze_fields = [str(x) for x in freeze["freeze_fields"]]
        elif isinstance(freeze.get("lock_fields"), list):
            freeze_fields = [str(x) for x in freeze["lock_fields"]]

    return max_machine_changes, max_start_shift, freeze_until, freeze_fields


JOBS, MACHINES, INSTANCE = parse_instance(INSTANCE_PATH)
DOWNTIME = load_downtime(DOWNTIME_PATH)
BASELINE = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
BASE_MAP = schedule_map(BASELINE)
BASE_INDEX = {(row["job"], row["op"]): idx for idx, row in enumerate(BASELINE)}
ORDER = sorted(BASE_MAP.keys(), key=lambda key: (key[1], BASE_MAP[key]["start"], BASE_INDEX[key]))
MAX_MC, MAX_SHIFT, FREEZE_UNTIL, FREEZE_FIELDS = parse_policy(POLICY_PATH)


def allowed_map(job: int, op: int) -> Dict[int, int]:
    return {machine: duration for machine, duration in INSTANCE[job][op]}


def is_frozen(base_row: Dict[str, int]) -> bool:
    return FREEZE_UNTIL is not None and bool(FREEZE_FIELDS) and base_row["start"] < FREEZE_UNTIL


machine_intervals: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
job_end: Dict[int, int] = defaultdict(int)
patched: List[Dict[str, int]] = []
machine_changes = 0
total_shift = 0

for job, op in ORDER:
    base_row = BASE_MAP[(job, op)]
    allowed = allowed_map(job, op)
    base_machine = base_row["machine"]
    base_start = base_row["start"]
    base_duration = allowed[base_machine]
    frozen = is_frozen(base_row)

    forced_machine = base_machine if (frozen and "machine" in FREEZE_FIELDS) else None
    forced_start = base_start if (frozen and "start" in FREEZE_FIELDS) else None
    forced_duration = base_duration if (frozen and "dur" in FREEZE_FIELDS) else None
    anchor = max(base_start, job_end[job])

    candidates: List[Tuple[int, int, int]] = []
    if forced_machine is not None:
        candidates = [(forced_machine, allowed[forced_machine], 0)]
    else:
        candidates.append((base_machine, base_duration, 0))
        for machine, duration in allowed.items():
            if machine != base_machine:
                candidates.append((machine, duration, 1))

    best = None
    for machine, duration, changed in candidates:
        if changed == 1 and machine_changes >= MAX_MC:
            continue
        if forced_duration is not None and duration != forced_duration:
            continue

        start_anchor = anchor if forced_start is None else max(anchor, forced_start)
        start = earliest_feasible_time(machine, start_anchor, duration, machine_intervals, DOWNTIME)
        end = start + duration

        if frozen and "end" in FREEZE_FIELDS and end != base_row["end"]:
            continue

        start_shift = abs(start - base_start)
        score = (changed, start_shift, end, start)
        if best is None or score < best[0]:
            best = (score, start, end, machine, duration)

    if best is None:
        raise RuntimeError(f"No feasible repair found for {(job, op)} within the declared policy budget")

    _, start, end, machine, duration = best
    machine_changes += int(machine != base_machine)
    total_shift += abs(start - base_start)

    if machine_changes > MAX_MC or total_shift > MAX_SHIFT:
        raise RuntimeError("Repair exceeded policy budget")

    machine_intervals[machine].append((start, end))
    machine_intervals[machine].sort()
    job_end[job] = end
    patched.append(
        {
            "job": job,
            "op": op,
            "machine": machine,
            "start": start,
            "end": end,
            "dur": duration,
        }
    )

patched.sort(key=lambda row: (row["start"], row["job"], row["op"]))
makespan = max((row["end"] for row in patched), default=0)

with open(SOLUTION_PATH, "w", encoding="utf-8") as f:
    json.dump({"status": "FEASIBLE", "makespan": makespan, "schedule": patched}, f, indent=2)
    f.write("\n")

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["job", "op", "machine", "start", "end", "dur"])
    writer.writeheader()
    writer.writerows(patched)
PY
