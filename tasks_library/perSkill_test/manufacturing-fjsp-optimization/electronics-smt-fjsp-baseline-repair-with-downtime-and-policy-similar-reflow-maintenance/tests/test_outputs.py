import csv
import json
import os
from collections import defaultdict
from functools import lru_cache
from typing import Any, Dict, List, Tuple

OUT_DIR = os.environ.get("OUT_DIR", "/app/output")
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

INSTANCE_PATH = os.path.join(DATA_DIR, "instance.txt")
DOWNTIME_PATH = os.path.join(DATA_DIR, "downtime.csv")
POLICY_PATH = os.path.join(DATA_DIR, "policy.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_solution.json")
BASELINE_METRICS_PATH = os.path.join(DATA_DIR, "baseline_metrics.json")
SOLUTION_PATH = os.path.join(OUT_DIR, "solution.json")
CSV_PATH = os.path.join(OUT_DIR, "schedule.csv")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a < d and c < b


def load_downtime(path: str) -> Dict[int, List[Tuple[int, int]]]:
    out: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    if not os.path.exists(path):
        return out
    for row in load_csv(path):
        out[int(row["machine"])].append((int(row["start"]), int(row["end"])))
    for machine in out:
        out[machine].sort()
    return out


def schedule_map(schedule: List[Dict[str, int]]) -> Dict[Tuple[int, int], Dict[str, int]]:
    return {(row["job"], row["op"]): row for row in schedule}


def tuple_key(row: Dict[str, int]) -> Tuple[int, int, int, int, int, int]:
    return (row["job"], row["op"], row["machine"], row["start"], row["end"], row["dur"])


def change_metrics(
    baseline: List[Dict[str, int]], patched: List[Dict[str, int]]
) -> Tuple[int, int]:
    bm = schedule_map(baseline)
    pm = schedule_map(patched)
    machine_changes = 0
    total_shift = 0
    for key, base_row in bm.items():
        new_row = pm[key]
        machine_changes += int(new_row["machine"] != base_row["machine"])
        total_shift += abs(new_row["start"] - base_row["start"])
    return machine_changes, total_shift


def downtime_violations(
    schedule: List[Dict[str, int]], downtime: Dict[int, List[Tuple[int, int]]]
) -> int:
    count = 0
    for row in schedule:
        for a, b in downtime.get(row["machine"], []):
            if overlap(row["start"], row["end"], a, b):
                count += 1
                break
    return count


def conflicts_with_machine_or_downtime(
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
        if not conflicts_with_machine_or_downtime(machine, t, t + duration, machine_intervals, downtime):
            return t
        t += 1


JOBS, MACHINES, INSTANCE = parse_instance(INSTANCE_PATH)
DOWNTIME = load_downtime(DOWNTIME_PATH)
POLICY = load_json(POLICY_PATH)
BASELINE = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
BASE_MAP = schedule_map(BASELINE)
BASE_INDEX = {(row["job"], row["op"]): i for i, row in enumerate(BASELINE)}
ORDER = sorted(BASE_MAP.keys(), key=lambda key: (key[1], BASE_MAP[key]["start"], BASE_INDEX[key]))
MAX_MC = int(POLICY["change_budget"]["max_machine_changes"])
MAX_SHIFT = int(POLICY["change_budget"]["max_total_start_shift_L1"])


@lru_cache(maxsize=1)
def compute_expected_optimum() -> Tuple[int, Tuple[Tuple[int, int, int, int, int, int], ...]]:
    best = None
    best_sched = None

    def dfs(
        idx: int,
        machine_intervals: Dict[int, List[Tuple[int, int]]],
        job_end: Dict[int, int],
        mc_used: int,
        shift_used: int,
        current: List[Dict[str, int]],
    ) -> None:
        nonlocal best, best_sched

        if idx == len(ORDER):
            sched = sorted(current, key=lambda row: (row["start"], row["job"], row["op"]))
            makespan = max(row["end"] for row in sched)
            score = (makespan, mc_used, shift_used, tuple(tuple_key(row) for row in sched))
            if best is None or score < best:
                best = score
                best_sched = tuple(tuple_key(row) for row in sched)
            return

        job, op = ORDER[idx]
        base_row = BASE_MAP[(job, op)]
        anchor = max(base_row["start"], job_end.get(job, 0))

        for machine, duration in INSTANCE[job][op]:
            start = earliest_feasible_time(machine, anchor, duration, machine_intervals, DOWNTIME)
            end = start + duration
            next_mc = mc_used + int(machine != base_row["machine"])
            next_shift = shift_used + abs(start - base_row["start"])

            if next_mc > MAX_MC or next_shift > MAX_SHIFT:
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
    assert best is not None and best_sched is not None, "Expected at least one feasible schedule"
    return best[0], best_sched


def test_required_outputs_exist() -> None:
    assert os.path.exists(SOLUTION_PATH), f"Missing {SOLUTION_PATH}"
    assert os.path.exists(CSV_PATH), f"Missing {CSV_PATH}"


def test_solution_shape_and_status() -> None:
    sol = load_json(SOLUTION_PATH)
    assert sol["status"] == "FEASIBLE"
    assert isinstance(sol["makespan"], int)
    normalize_schedule(sol["schedule"])


def test_schedule_matches_instance_domain() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    expected_keys = {(j, o) for j in range(JOBS) for o in range(len(INSTANCE[j]))}
    assert {(row["job"], row["op"]) for row in sched} == expected_keys
    assert len(sched) == len(expected_keys)

    allowed = {
        (j, o): {machine: duration for machine, duration in INSTANCE[j][o]}
        for j in range(JOBS)
        for o in range(len(INSTANCE[j]))
    }
    for row in sched:
        key = (row["job"], row["op"])
        assert 0 <= row["machine"] < MACHINES
        assert row["start"] >= 0
        assert row["machine"] in allowed[key]
        assert row["dur"] == allowed[key][row["machine"]]
        assert row["end"] == row["start"] + row["dur"]


def test_precedence_machine_overlap_and_downtime() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    by_job = schedule_map(sched)
    for j in range(JOBS):
        for o in range(len(INSTANCE[j]) - 1):
            assert by_job[(j, o)]["end"] <= by_job[(j, o + 1)]["start"]

    by_machine: Dict[int, List[Tuple[int, int, int, int]]] = defaultdict(list)
    for row in sched:
        by_machine[row["machine"]].append((row["start"], row["end"], row["job"], row["op"]))
    for machine, rows in by_machine.items():
        rows.sort()
        for left, right in zip(rows, rows[1:]):
            assert left[1] <= right[0], f"Machine overlap on machine {machine}: {left} vs {right}"

    assert downtime_violations(sched, DOWNTIME) == 0


def test_policy_budget_and_right_shift_only() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    machine_changes, total_shift = change_metrics(BASELINE, sched)
    assert machine_changes <= MAX_MC
    assert total_shift <= MAX_SHIFT

    base_map = schedule_map(BASELINE)
    for row in sched:
        assert row["start"] >= base_map[(row["job"], row["op"])]["start"]


def test_local_minimal_right_shift_in_precedence_order() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    pm = schedule_map(sched)
    machine_intervals: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    job_end: Dict[int, int] = defaultdict(int)

    for key in ORDER:
        base_row = BASE_MAP[key]
        patched_row = pm[key]
        anchor = max(base_row["start"], job_end[patched_row["job"]])
        assert patched_row["start"] >= anchor

        if patched_row["start"] > anchor:
            candidate = patched_row["start"] - 1
            assert conflicts_with_machine_or_downtime(
                patched_row["machine"],
                candidate,
                candidate + patched_row["dur"],
                machine_intervals,
                DOWNTIME,
            )

        machine_intervals[patched_row["machine"]].append((patched_row["start"], patched_row["end"]))
        machine_intervals[patched_row["machine"]].sort()
        job_end[patched_row["job"]] = patched_row["end"]


def test_must_improve_baseline_metrics() -> None:
    sol = load_json(SOLUTION_PATH)
    sched = normalize_schedule(sol["schedule"])
    baseline_metrics = load_json(BASELINE_METRICS_PATH)
    assert baseline_metrics["baseline"]["downtime_violations"] > 0
    assert downtime_violations(sched, DOWNTIME) == 0
    assert sol["makespan"] < int(baseline_metrics["baseline"]["makespan"])


def test_matches_exact_optimum() -> None:
    expected_makespan, expected_schedule = compute_expected_optimum()
    sol = load_json(SOLUTION_PATH)
    sched = tuple(sorted((tuple_key(row) for row in normalize_schedule(sol["schedule"]))))
    assert sol["makespan"] == expected_makespan == 31
    assert sched == tuple(sorted(expected_schedule))

    machine_changes, total_shift = change_metrics(BASELINE, normalize_schedule(sol["schedule"]))
    assert machine_changes == 4
    assert total_shift == 31


def test_csv_matches_solution() -> None:
    sol_sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    csv_sched = normalize_schedule(load_csv(CSV_PATH))
    assert set(tuple_key(row) for row in sol_sched) == set(tuple_key(row) for row in csv_sched)
