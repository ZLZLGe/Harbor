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
from typing import Any, Dict, List, Tuple

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
            alts: List[Tuple[int, int]] = []
            for _ in range(k):
                m = int(next(it))
                d = int(next(it))
                alts.append((m, d))
            ops.append(alts)
        parsed.append(ops)
    return jobs, machines, parsed


def load_downtime(path: str) -> Dict[int, List[Tuple[int, int]]]:
    by_machine: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    if not os.path.exists(path):
        return by_machine
    for row in load_csv(path):
        by_machine[int(row["machine"])].append((int(row["start"]), int(row["end"])))
    for machine in by_machine:
        by_machine[machine].sort()
    return by_machine


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


def normalized_schedule(rows: List[Dict[str, Any]]) -> List[Dict[str, int]]:
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


_, _, jobs = parse_instance(INSTANCE_PATH)
downtime = load_downtime(DOWNTIME_PATH)
policy = load_json(POLICY_PATH)
baseline = normalized_schedule(load_json(BASELINE_PATH)["schedule"])
base_map = {(row["job"], row["op"]): row for row in baseline}
base_index = {(row["job"], row["op"]): i for i, row in enumerate(baseline)}
order = sorted(base_map.keys(), key=lambda key: (key[1], base_map[key]["start"], base_index[key]))

max_machine_changes = int(policy["change_budget"]["max_machine_changes"])
max_total_shift = int(policy["change_budget"]["max_total_start_shift_L1"])

best_score = None
best_schedule = None


def dfs(
    idx: int,
    machine_intervals: Dict[int, List[Tuple[int, int]]],
    job_end: Dict[int, int],
    mc_used: int,
    shift_used: int,
    current: List[Dict[str, int]],
) -> None:
    global best_score, best_schedule

    if idx == len(order):
        schedule = sorted(current, key=lambda row: (row["start"], row["job"], row["op"]))
        makespan = max((row["end"] for row in schedule), default=0)
        score = (makespan, mc_used, shift_used, tuple((r["job"], r["op"], r["machine"], r["start"]) for r in schedule))
        if best_score is None or score < best_score:
            best_score = score
            best_schedule = schedule
        return

    key = order[idx]
    job, op = key
    base_row = base_map[key]
    anchor = max(base_row["start"], job_end.get(job, 0))

    for machine, duration in jobs[job][op]:
        start = earliest_feasible_time(machine, anchor, duration, machine_intervals, downtime)
        end = start + duration
        next_mc = mc_used + int(machine != base_row["machine"])
        next_shift = shift_used + abs(start - base_row["start"])

        if next_mc > max_machine_changes or next_shift > max_total_shift:
            continue

        next_machine_intervals = {m: list(intervals) for m, intervals in machine_intervals.items()}
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
        dfs(idx + 1, next_machine_intervals, next_job_end, next_mc, next_shift, current)
        current.pop()


dfs(0, {}, {}, 0, 0, [])

if best_schedule is None:
    raise SystemExit("No feasible repaired schedule found within budget.")

solution = {
    "status": "FEASIBLE",
    "makespan": max(row["end"] for row in best_schedule),
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
