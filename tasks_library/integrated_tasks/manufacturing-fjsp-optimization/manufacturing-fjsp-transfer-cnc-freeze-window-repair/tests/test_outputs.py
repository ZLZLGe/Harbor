import csv
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

APP_ROOT = os.environ.get("APP_ROOT", "/app")
OUT_DIR = f"{APP_ROOT}/output"
DATA_DIR = f"{APP_ROOT}/data"

INSTANCE_PATH = f"{DATA_DIR}/cnc_instance.txt"
DOWNTIME_PATH = f"{DATA_DIR}/maintenance_windows.csv"
POLICY_PATH = f"{DATA_DIR}/recovery_policy.json"
OLD_METRICS_PATH = f"{DATA_DIR}/baseline_metrics.json"
OLD_PLAN_PATH = f"{DATA_DIR}/baseline_cnc_plan.json"

PLAN_JSON = f"{OUT_DIR}/cnc_recovery_plan.json"
PLAN_CSV = f"{OUT_DIR}/cnc_recovery_plan.csv"


def load_json(path: str) -> Any:
    assert os.path.exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: str) -> List[Dict[str, str]]:
    assert os.path.exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        assert abs(value - round(value)) < 1e-9
        return int(round(value))
    return int(str(value).strip())


def parse_instance(path: str) -> Tuple[int, int, List[List[List[Tuple[int, int]]]]]:
    tokens: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            tokens.extend(stripped.split())

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


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a < d and c < b


def normalize_schedule(raw: Any) -> List[Dict[str, int]]:
    assert isinstance(raw, list), "schedule must be a list"
    schedule: List[Dict[str, int]] = []
    for row in raw:
        assert isinstance(row, dict), "each schedule row must be an object"
        schedule.append({
            "job": as_int(row["job"]),
            "op": as_int(row["op"]),
            "machine": as_int(row["machine"]),
            "start": as_int(row["start"]),
            "end": as_int(row["end"]),
            "dur": as_int(row["dur"]),
        })
    return schedule


def sched_map(schedule: List[Dict[str, int]]) -> Dict[Tuple[int, int], Dict[str, int]]:
    return {(row["job"], row["op"]): row for row in schedule}


def tuple_key(row: Dict[str, int]) -> Tuple[int, int, int, int, int, int]:
    return (row["job"], row["op"], row["machine"], row["start"], row["end"], row["dur"])


def load_downtime() -> Dict[int, List[Tuple[int, int]]]:
    downtime: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    for row in load_csv(DOWNTIME_PATH):
        downtime[as_int(row["machine"])].append((as_int(row["start"]), as_int(row["end"])))
    for machine in downtime:
        downtime[machine].sort()
    return downtime


def count_downtime_violations(schedule: List[Dict[str, int]], downtime: Dict[int, List[Tuple[int, int]]]) -> int:
    violations = 0
    for row in schedule:
        for start, end in downtime.get(row["machine"], []):
            if overlap(row["start"], row["end"], start, end):
                violations += 1
                break
    return violations


def parse_policy() -> Tuple[int, List[str], Dict[str, int]]:
    policy = load_json(POLICY_PATH)
    freeze = {}
    if isinstance(policy.get("freeze_window"), dict):
        freeze = policy["freeze_window"]
    elif isinstance(policy.get("freeze"), dict):
        freeze = policy["freeze"]

    freeze_until = as_int(freeze.get("freeze_until", freeze.get("until", policy.get("freeze_until", 0))))
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
    return freeze_until, locked_fields, {
        "max_machine_changes": as_int(budget.get("max_machine_changes", 10**9)),
        "max_total_start_shift_L1": as_int(budget.get("max_total_start_shift_L1", 10**18)),
    }


def change_metrics(patched: List[Dict[str, int]], baseline: List[Dict[str, int]]) -> Tuple[int, int]:
    patched_map = sched_map(patched)
    baseline_map = sched_map(baseline)
    machine_changes = 0
    total_shift = 0
    for key, base_row in baseline_map.items():
        patched_row = patched_map[key]
        machine_changes += int(base_row["machine"] != patched_row["machine"])
        total_shift += abs(base_row["start"] - patched_row["start"])
    return machine_changes, total_shift


def precedence_aware_order(base_list: List[Dict[str, int]]) -> List[Tuple[int, int]]:
    base_map = sched_map(base_list)
    base_index = {(row["job"], row["op"]): idx for idx, row in enumerate(base_list)}
    keys = list(base_map.keys())
    keys.sort(key=lambda key: (key[1], base_map[key]["start"], base_index[key]))
    return keys


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


def test_L0_outputs_exist():
    assert os.path.exists(PLAN_JSON), f"Missing required output: {PLAN_JSON}"
    assert os.path.exists(PLAN_CSV), f"Missing required output: {PLAN_CSV}"


def test_L0_json_shape():
    payload = load_json(PLAN_JSON)
    assert isinstance(payload, dict)
    assert isinstance(payload.get("status"), str) and payload["status"].strip()
    assert as_int(payload["makespan"]) >= 0
    assert as_int(payload["machine_changes"]) >= 0
    assert as_int(payload["total_start_shift"]) >= 0
    _ = normalize_schedule(payload["schedule"])


def test_L1_complete_unique_and_allowed():
    jobs_n, machines_n, jobs = parse_instance(INSTANCE_PATH)
    payload = load_json(PLAN_JSON)
    schedule = normalize_schedule(payload["schedule"])

    expected = {(job, op) for job in range(jobs_n) for op in range(len(jobs[job]))}
    got = {(row["job"], row["op"]) for row in schedule}
    assert got == expected
    assert len(schedule) == len(expected)

    allowed: Dict[Tuple[int, int], Dict[int, int]] = {}
    for job in range(jobs_n):
        for op in range(len(jobs[job])):
            allowed[(job, op)] = {machine: dur for machine, dur in jobs[job][op]}

    for row in schedule:
        key = (row["job"], row["op"])
        assert 0 <= row["machine"] < machines_n
        assert row["start"] >= 0
        assert row["dur"] > 0
        assert row["end"] == row["start"] + row["dur"]
        assert row["machine"] in allowed[key]
        assert row["dur"] == allowed[key][row["machine"]]


def test_L1_precedence_and_machine_capacity():
    jobs_n, _, jobs = parse_instance(INSTANCE_PATH)
    schedule = normalize_schedule(load_json(PLAN_JSON)["schedule"])
    schedule_map = sched_map(schedule)

    for job in range(jobs_n):
        for op in range(len(jobs[job]) - 1):
            assert schedule_map[(job, op)]["end"] <= schedule_map[(job, op + 1)]["start"]

    by_machine: Dict[int, List[Tuple[int, int, int, int]]] = defaultdict(list)
    for row in schedule:
        by_machine[row["machine"]].append((row["start"], row["end"], row["job"], row["op"]))
    for machine, rows in by_machine.items():
        rows.sort()
        for idx in range(len(rows) - 1):
            assert rows[idx][1] <= rows[idx + 1][0], f"Machine overlap on machine {machine}"


def test_L1_makespan_and_csv_match():
    payload = load_json(PLAN_JSON)
    schedule = normalize_schedule(payload["schedule"])
    makespan = max((row["end"] for row in schedule), default=0)
    assert as_int(payload["makespan"]) == makespan

    csv_rows = [{
        "job": as_int(row["job"]),
        "op": as_int(row["op"]),
        "machine": as_int(row["machine"]),
        "start": as_int(row["start"]),
        "end": as_int(row["end"]),
        "dur": as_int(row["dur"]),
    } for row in load_csv(PLAN_CSV)]
    assert set(map(tuple_key, csv_rows)) == set(map(tuple_key, schedule))


def test_L2_no_downtime_overlap_and_improves_baseline():
    downtime = load_downtime()
    schedule = normalize_schedule(load_json(PLAN_JSON)["schedule"])
    baseline = normalize_schedule(load_json(OLD_PLAN_PATH)["schedule"])
    baseline_violations = as_int(load_json(OLD_METRICS_PATH)["baseline"]["downtime_violations"])
    assert baseline_violations > 0
    assert count_downtime_violations(schedule, downtime) == 0
    assert count_downtime_violations(schedule, downtime) < count_downtime_violations(baseline, downtime)


def test_L3_right_shift_freeze_and_budget():
    freeze_until, locked_fields, budget = parse_policy()
    baseline = normalize_schedule(load_json(OLD_PLAN_PATH)["schedule"])
    repaired = normalize_schedule(load_json(PLAN_JSON)["schedule"])
    baseline_map = sched_map(baseline)
    repaired_map = sched_map(repaired)

    for key, repaired_row in repaired_map.items():
        base_row = baseline_map[key]
        assert repaired_row["start"] >= base_row["start"], f"Right-shift violated for {key}"
        if base_row["start"] < freeze_until:
            for field in locked_fields:
                if field in base_row and field in repaired_row:
                    assert repaired_row[field] == base_row[field], f"Freeze violated for {key} field {field}"

    machine_changes, total_shift = change_metrics(repaired, baseline)
    payload = load_json(PLAN_JSON)
    assert machine_changes == as_int(payload["machine_changes"])
    assert total_shift == as_int(payload["total_start_shift"])
    assert machine_changes <= budget["max_machine_changes"]
    assert total_shift <= budget["max_total_start_shift_L1"]


def test_L3_local_minimal_right_shift_in_precedence_order():
    downtime = load_downtime()
    baseline = normalize_schedule(load_json(OLD_PLAN_PATH)["schedule"])
    repaired = normalize_schedule(load_json(PLAN_JSON)["schedule"])
    baseline_map = sched_map(baseline)
    repaired_map = sched_map(repaired)
    order = precedence_aware_order(baseline)

    machine_intervals: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    job_end: Dict[int, int] = defaultdict(int)

    for key in order:
        base_row = baseline_map[key]
        repaired_row = repaired_map[key]
        anchor = max(base_row["start"], job_end[key[0]])
        assert repaired_row["start"] >= anchor

        if repaired_row["start"] > anchor:
            candidate_start = repaired_row["start"] - 1
            assert conflicts_with_machine_or_downtime(
                repaired_row["machine"],
                candidate_start,
                candidate_start + repaired_row["dur"],
                machine_intervals,
                downtime,
            ), f"Placement is not locally minimal for {key}"

        machine_intervals[repaired_row["machine"]].append((repaired_row["start"], repaired_row["end"]))
        machine_intervals[repaired_row["machine"]].sort()
        job_end[key[0]] = repaired_row["end"]
