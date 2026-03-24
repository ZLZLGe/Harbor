#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
from typing import Any, Dict, List, Tuple

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

INSTANCE_PATH = os.path.join(DATA_DIR, "instance.txt")
DOWNTIME_PATH = os.path.join(DATA_DIR, "downtime.csv")
POLICY_PATH = os.path.join(DATA_DIR, "policy.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_solution.json")

SOLUTION_PATH = os.path.join(OUT_DIR, "solution.json")
CSV_PATH = os.path.join(OUT_DIR, "schedule.csv")

os.makedirs(OUT_DIR, exist_ok=True)


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


def schedule_map(schedule: List[Dict[str, int]]) -> Dict[Tuple[int, int], Dict[str, int]]:
    return {(row["job"], row["op"]): row for row in schedule}


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a < d and c < b


def load_downtime(path: str) -> Dict[int, List[Tuple[int, int]]]:
    out: Dict[int, List[Tuple[int, int]]] = {}
    for row in load_csv(path):
        machine = int(row["machine"])
        out.setdefault(machine, []).append((int(row["start"]), int(row["end"])))
    for machine in out:
        out[machine].sort()
    return out


def earliest_feasible_time(
    machine: int,
    anchor: int,
    duration: int,
    machine_intervals: Dict[int, List[Tuple[int, int]]],
    downtime: Dict[int, List[Tuple[int, int]]],
) -> int:
    t = int(anchor)
    while True:
        end = t + duration
        blocked = False
        for a, b in machine_intervals.get(machine, []):
            if overlap(t, end, a, b):
                blocked = True
                break
        if not blocked:
            for a, b in downtime.get(machine, []):
                if overlap(t, end, a, b):
                    blocked = True
                    break
        if not blocked:
            return t
        t += 1


def tuple_key(row: Dict[str, int]) -> Tuple[int, int, int, int, int, int]:
    return (row["job"], row["op"], row["machine"], row["start"], row["end"], row["dur"])


jobs_count, machine_count, instance = parse_instance(INSTANCE_PATH)
downtime = load_downtime(DOWNTIME_PATH)
policy = load_json(POLICY_PATH)
baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])

freeze = policy.get("freeze", {})
freeze_until = int(freeze["until"])
freeze_fields = set(freeze["fields"])
max_machine_changes = int(policy["change_budget"]["max_machine_changes"])
max_total_shift = int(policy["change_budget"]["max_total_start_shift_L1"])

base_map = schedule_map(baseline)
base_index = {(row["job"], row["op"]): idx for idx, row in enumerate(baseline)}
order = sorted(base_map.keys(), key=lambda key: (key[1], base_map[key]["start"], base_index[key]))

best_score = None
best_schedule: List[Dict[str, int]] | None = None


def dfs(
    idx: int,
    machine_intervals: Dict[int, List[Tuple[int, int]]],
    job_end: Dict[int, int],
    machine_changes: int,
    total_shift: int,
    current: List[Dict[str, int]],
    current_max_end: int,
) -> None:
    global best_score, best_schedule

    if best_score is not None and current_max_end > best_score[0]:
        return

    if idx == len(order):
        schedule = sorted(current, key=lambda row: (row["start"], row["job"], row["op"]))
        makespan = max((row["end"] for row in schedule), default=0)
        score = (makespan, machine_changes, total_shift, tuple(tuple_key(row) for row in schedule))
        if best_score is None or score < best_score:
            best_score = score
            best_schedule = [dict(row) for row in schedule]
        return

    job, op = order[idx]
    base_row = base_map[(job, op)]
    anchor = max(base_row["start"], job_end.get(job, 0))
    allowed = instance[job][op]
    frozen = base_row["start"] < freeze_until and bool(freeze_fields)

    if frozen and "machine" in freeze_fields:
        allowed = [(base_row["machine"], dict(instance[job][op])[base_row["machine"]])]

    for machine, duration in allowed:
        start = earliest_feasible_time(machine, anchor, duration, machine_intervals, downtime)
        end = start + duration

        if frozen and "start" in freeze_fields and start != base_row["start"]:
            continue
        if frozen and "end" in freeze_fields and end != base_row["end"]:
            continue

        next_machine_changes = machine_changes + int(machine != base_row["machine"])
        next_total_shift = total_shift + abs(start - base_row["start"])
        if next_machine_changes > max_machine_changes or next_total_shift > max_total_shift:
            continue

        next_machine_intervals = {m: list(v) for m, v in machine_intervals.items()}
        next_machine_intervals.setdefault(machine, []).append((start, end))
        next_machine_intervals[machine].sort()

        next_job_end = dict(job_end)
        next_job_end[job] = end

        current.append(
            {
                "job": job,
                "op": op,
                "machine": machine,
                "start": start,
                "end": end,
                "dur": duration,
            }
        )
        dfs(
            idx + 1,
            next_machine_intervals,
            next_job_end,
            next_machine_changes,
            next_total_shift,
            current,
            max(current_max_end, end),
        )
        current.pop()


dfs(0, {}, {}, 0, 0, [], 0)
assert best_schedule is not None, "No feasible repaired schedule found"

solution = {
    "status": "FEASIBLE",
    "makespan": int(best_score[0]),
    "schedule": best_schedule,
}

with open(SOLUTION_PATH, "w", encoding="utf-8") as f:
    json.dump(solution, f, indent=2)

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["job", "op", "machine", "start", "end", "dur"])
    writer.writeheader()
    for row in best_schedule:
        writer.writerow(row)
PY
