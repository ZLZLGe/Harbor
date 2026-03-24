import csv
import json
import os
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


def tuple_key(row: Dict[str, int]) -> Tuple[int, int, int, int, int, int]:
    return (row["job"], row["op"], row["machine"], row["start"], row["end"], row["dur"])


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


def change_metrics(
    baseline: List[Dict[str, int]], patched: List[Dict[str, int]]
) -> Tuple[int, int]:
    bm = schedule_map(baseline)
    pm = schedule_map(patched)
    machine_changes = 0
    total_shift = 0
    for key, base_row in bm.items():
        machine_changes += int(pm[key]["machine"] != base_row["machine"])
        total_shift += abs(pm[key]["start"] - base_row["start"])
    return machine_changes, total_shift


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
def expected_optimum() -> Tuple[Tuple[int, int, int], Tuple[Tuple[int, int, int, int, int, int], ...]]:
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
    assert best_score is not None and best_schedule is not None
    return best_score[:3], best_schedule


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


def test_precedence_machine_capacity_and_makespan() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    sched_by_key = schedule_map(sched)

    for job in range(JOBS):
        for op in range(len(INSTANCE[job]) - 1):
            assert sched_by_key[(job, op)]["end"] <= sched_by_key[(job, op + 1)]["start"]

    by_machine: Dict[int, List[Tuple[int, int]]] = {}
    for row in sched:
        by_machine.setdefault(row["machine"], []).append((row["start"], row["end"]))
    for intervals in by_machine.values():
        intervals.sort()
        for idx in range(len(intervals) - 1):
            assert intervals[idx][1] <= intervals[idx + 1][0]

    assert load_json(SOLUTION_PATH)["makespan"] == max(row["end"] for row in sched)


def test_no_downtime_and_budget_violations() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    assert downtime_violations(sched, DOWNTIME) == 0
    machine_changes, total_shift = change_metrics(BASELINE, sched)
    assert machine_changes <= MAX_MC
    assert total_shift <= MAX_SHIFT


def test_right_shift_and_local_minimality() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    patched = schedule_map(sched)
    machine_intervals: Dict[int, List[Tuple[int, int]]] = {}
    job_end: Dict[int, int] = {}

    for key in ORDER:
        base_row = BASE_MAP[key]
        row = patched[key]
        anchor = max(base_row["start"], job_end.get(key[0], 0))
        assert row["start"] >= base_row["start"]
        expected = earliest_feasible_time(
            row["machine"], anchor, row["dur"], machine_intervals, DOWNTIME
        )
        assert row["start"] == expected

        machine_intervals.setdefault(row["machine"], []).append((row["start"], row["end"]))
        machine_intervals[row["machine"]].sort()
        job_end[key[0]] = row["end"]


def test_illegal_baseline_machine_is_repaired() -> None:
    illegal_key = (2, 1)
    allowed_machines = {machine for machine, _ in INSTANCE[illegal_key[0]][illegal_key[1]]}
    assert BASE_MAP[illegal_key]["machine"] not in allowed_machines

    sched = schedule_map(normalize_schedule(load_json(SOLUTION_PATH)["schedule"]))
    assert sched[illegal_key]["machine"] in allowed_machines
    assert sched[illegal_key]["machine"] != BASE_MAP[illegal_key]["machine"]


def test_baseline_metrics_are_consistent_and_improved() -> None:
    metrics = load_json(BASELINE_METRICS_PATH)
    baseline_violations = downtime_violations(BASELINE, DOWNTIME)
    assert metrics["baseline"]["makespan"] == max(row["end"] for row in BASELINE)
    assert metrics["baseline"]["downtime_violations"] == baseline_violations
    assert baseline_violations > 0

    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    assert downtime_violations(sched, DOWNTIME) < baseline_violations


def test_matches_exhaustive_optimum() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    machine_changes, total_shift = change_metrics(BASELINE, sched)
    expected_score, expected_schedule = expected_optimum()
    actual_schedule = tuple(sorted((tuple_key(row) for row in sched), key=lambda row: (row[3], row[0], row[1])))
    actual_score = (load_json(SOLUTION_PATH)["makespan"], machine_changes, total_shift)
    assert actual_score == expected_score
    assert actual_schedule == expected_schedule


def test_csv_matches_solution() -> None:
    sched = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    csv_rows = normalize_schedule(load_csv(CSV_PATH))
    assert set(tuple_key(row) for row in sched) == set(tuple_key(row) for row in csv_rows)
