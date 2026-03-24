#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUT_DIR="${OUT_DIR:-/app/output}"
mkdir -p "${OUT_DIR}"

DATA_DIR="${DATA_DIR}" OUT_DIR="${OUT_DIR}" python3 - <<'PY'
import csv
import json
import os
from functools import lru_cache
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
                alts.append((int(next(it)), int(next(it))))
            ops.append(alts)
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


def tuple_key(row: Dict[str, int]) -> Tuple[int, int, int, int, int, int]:
    return (row["job"], row["op"], row["machine"], row["start"], row["end"], row["dur"])


JOBS, MACHINES, INSTANCE = parse_instance(INSTANCE_PATH)
DOWNTIME = load_downtime(DOWNTIME_PATH)
POLICY = load_json(POLICY_PATH)
BASELINE = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
BASE_MAP = schedule_map(BASELINE)
BASE_INDEX = {(row["job"], row["op"]): idx for idx, row in enumerate(BASELINE)}
ORDER = sorted(BASE_MAP.keys(), key=lambda key: (key[1], BASE_MAP[key]["start"], BASE_INDEX[key]))
MAX_MC = int(POLICY["change_budget"]["max_machine_changes"])
MAX_SHIFT = int(POLICY["change_budget"]["max_total_start_shift_L1"])


@lru_cache(maxsize=1)
def solve_optimum() -> Tuple[Tuple[int, int, int], Tuple[Tuple[int, int, int, int, int, int], ...]]:
    best_score = None
    best_schedule = None

    def dfs(
        idx: int,
        machine_intervals: Dict[int, List[Tuple[int, int]]],
        job_end: Dict[int, int],
        machine_changes: int,
        total_shift: int,
        current: List[Tuple[int, int, int, int, int, int]],
        current_max_end: int,
    ) -> None:
        nonlocal best_score, best_schedule

        if best_score is not None and current_max_end > best_score[0]:
            return

        if idx == len(ORDER):
            schedule = tuple(sorted(current, key=lambda row: (row[3], row[0], row[1])))
            score = (current_max_end, machine_changes, total_shift, schedule)
            if best_score is None or score < best_score:
                best_score = score
                best_schedule = schedule
            return

        job, op = ORDER[idx]
        base_row = BASE_MAP[(job, op)]
        anchor = max(base_row["start"], job_end.get(job, 0))

        for machine, duration in INSTANCE[job][op]:
            start = earliest_feasible_time(machine, anchor, duration, machine_intervals, DOWNTIME)
            end = start + duration
            next_machine_changes = machine_changes + int(machine != base_row["machine"])
            next_total_shift = total_shift + abs(start - base_row["start"])

            if next_machine_changes > MAX_MC or next_total_shift > MAX_SHIFT:
                continue

            next_machine_intervals = {m: list(v) for m, v in machine_intervals.items()}
            next_machine_intervals.setdefault(machine, []).append((start, end))
            next_machine_intervals[machine].sort()

            next_job_end = dict(job_end)
            next_job_end[job] = end

            current.append((job, op, machine, start, end, duration))
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
    if best_score is None or best_schedule is None:
        raise SystemExit("No feasible repaired schedule found within budget.")
    return best_score[:3], best_schedule


(makespan, _, _), best_schedule = solve_optimum()
schedule = [
    {
        "job": row[0],
        "op": row[1],
        "machine": row[2],
        "start": row[3],
        "end": row[4],
        "dur": row[5],
    }
    for row in best_schedule
]

solution = {
    "status": "FEASIBLE",
    "makespan": makespan,
    "schedule": schedule,
}

with open(SOLUTION_PATH, "w", encoding="utf-8") as f:
    json.dump(solution, f, indent=2)

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["job", "op", "machine", "start", "end", "dur"])
    writer.writeheader()
    for row in schedule:
        writer.writerow(row)
PY
