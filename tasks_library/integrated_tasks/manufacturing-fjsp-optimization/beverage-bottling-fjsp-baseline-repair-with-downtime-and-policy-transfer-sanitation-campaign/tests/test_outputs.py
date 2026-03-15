import csv
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

OUT_DIR = os.environ.get("OUT_DIR", "/app/output")
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

INSTANCE_PATH = os.path.join(DATA_DIR, "instance.txt")
DOWNTIME_PATH = os.path.join(DATA_DIR, "downtime.csv")
POLICY_PATH = os.path.join(DATA_DIR, "policy.json")
BASELINE_METRICS_PATH = os.path.join(DATA_DIR, "baseline_metrics.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_solution.json")
SOLUTION_PATH = os.path.join(OUT_DIR, "solution.json")
CSV_PATH = os.path.join(OUT_DIR, "schedule.csv")


def exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False


def load_json(path: str) -> Any:
    assert exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: str) -> List[Dict[str, str]]:
    assert exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        assert abs(value - round(value)) < 1e-9, f"Expected integer-like float, got {value}"
        return int(round(value))
    if isinstance(value, str):
        text = value.strip()
        if "." in text:
            parsed = float(text)
            assert abs(parsed - round(parsed)) < 1e-9, f"Expected integer-like string float, got {value}"
            return int(round(parsed))
        return int(text)
    return int(value)


def overlap(a: int, b: int, c: int, d: int) -> bool:
    return a < d and c < b


def parse_instance(path: str) -> Tuple[int, int, List[List[List[Tuple[int, int]]]]]:
    tokens: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            tokens.extend(stripped.split())
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


def load_downtime() -> Dict[int, List[Tuple[int, int]]]:
    if not exists(DOWNTIME_PATH):
        return {}
    out: Dict[int, List[Tuple[int, int]]] = {}
    for row in load_csv(DOWNTIME_PATH):
        machine = as_int(row["machine"])
        out.setdefault(machine, []).append((as_int(row["start"]), as_int(row["end"])))
    for machine in out:
        out[machine].sort()
    return out


def normalize_schedule(raw: Any) -> List[Dict[str, int]]:
    assert isinstance(raw, list), "schedule must be a list"
    out: List[Dict[str, int]] = []
    for row in raw:
        assert isinstance(row, dict), "each schedule row must be an object"
        for key in ("job", "op", "machine", "start", "end", "dur"):
            assert key in row, f"schedule row missing '{key}'"
        out.append(
            {
                "job": as_int(row["job"]),
                "op": as_int(row["op"]),
                "machine": as_int(row["machine"]),
                "start": as_int(row["start"]),
                "end": as_int(row["end"]),
                "dur": as_int(row["dur"]),
            }
        )
    return out


def schedule_map(schedule: List[Dict[str, int]]) -> Dict[Tuple[int, int], Dict[str, int]]:
    return {(row["job"], row["op"]): row for row in schedule}


def count_downtime_violations(
    schedule: List[Dict[str, int]], downtime: Dict[int, List[Tuple[int, int]]]
) -> int:
    violations = 0
    for row in schedule:
        for start, end in downtime.get(row["machine"], []):
            if overlap(row["start"], row["end"], start, end):
                violations += 1
                break
    return violations


def get_policy() -> Dict[str, Any]:
    if not exists(POLICY_PATH):
        return {}
    policy = load_json(POLICY_PATH)
    return policy if isinstance(policy, dict) else {}


def get_change_budget(policy: Dict[str, Any]) -> Dict[str, int]:
    budget = policy.get("change_budget", {}) if isinstance(policy, dict) else {}
    return {
        "max_machine_changes": as_int(budget.get("max_machine_changes", 10**9)),
        "max_total_start_shift_L1": as_int(budget.get("max_total_start_shift_L1", 10**18)),
    }


def get_freeze_policy(policy: Dict[str, Any]) -> Tuple[Optional[int], List[str]]:
    freeze_until = None
    freeze_fields: List[str] = []
    if not isinstance(policy, dict):
        return freeze_until, freeze_fields

    freeze = policy.get("freeze")
    if isinstance(freeze, dict):
        if freeze.get("until") is not None:
            freeze_until = as_int(freeze["until"])
        elif freeze.get("freeze_until") is not None:
            freeze_until = as_int(freeze["freeze_until"])

        if isinstance(freeze.get("fields"), list):
            freeze_fields = [str(item) for item in freeze["fields"]]
        elif isinstance(freeze.get("freeze_fields"), list):
            freeze_fields = [str(item) for item in freeze["freeze_fields"]]
        elif isinstance(freeze.get("lock_fields"), list):
            freeze_fields = [str(item) for item in freeze["lock_fields"]]
    else:
        if policy.get("freeze_until") is not None:
            freeze_until = as_int(policy["freeze_until"])
        if isinstance(policy.get("freeze_fields"), list):
            freeze_fields = [str(item) for item in policy["freeze_fields"]]

    return freeze_until, freeze_fields


def change_metrics(
    patched: List[Dict[str, int]], baseline: List[Dict[str, int]]
) -> Tuple[int, int]:
    patched_map = schedule_map(patched)
    baseline_map = schedule_map(baseline)
    assert set(patched_map.keys()) == set(baseline_map.keys()), "Patched and baseline must share the same (job, op) keys"
    machine_changes = sum(patched_map[key]["machine"] != baseline_map[key]["machine"] for key in baseline_map)
    total_shift = sum(abs(patched_map[key]["start"] - baseline_map[key]["start"]) for key in baseline_map)
    return machine_changes, total_shift


def tuple_key(row: Dict[str, int]) -> Tuple[int, int, int, int, int, int]:
    return (row["job"], row["op"], row["machine"], row["start"], row["end"], row["dur"])


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


def precedence_aware_repair_order(baseline_list: List[Dict[str, int]]) -> List[Tuple[int, int]]:
    baseline_map = schedule_map(baseline_list)
    baseline_index = {(row["job"], row["op"]): idx for idx, row in enumerate(baseline_list)}
    keys = [(row["job"], row["op"]) for row in baseline_list]
    keys.sort(key=lambda key: (key[1], baseline_map[key]["start"], baseline_index[key]))
    return keys


def test_L0_required_outputs_exist() -> None:
    assert exists(SOLUTION_PATH), f"Missing required output: {SOLUTION_PATH}"
    assert exists(CSV_PATH), f"Missing required output: {CSV_PATH}"


def test_L0_solution_has_minimum_fields() -> None:
    solution = load_json(SOLUTION_PATH)
    assert isinstance(solution, dict)
    assert isinstance(solution.get("status"), str) and solution["status"].strip()
    assert "makespan" in solution
    assert "schedule" in solution
    _ = as_int(solution["makespan"])
    _ = normalize_schedule(solution["schedule"])


def test_L1_complete_ops_unique_and_valid_against_instance() -> None:
    jobs, machines, instance = parse_instance(INSTANCE_PATH)
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])

    expected = {(job, op) for job in range(jobs) for op in range(len(instance[job]))}
    got = {(row["job"], row["op"]) for row in schedule}
    assert got == expected, f"Schedule missing or extra ops. expected={len(expected)} got={len(got)}"
    assert len(schedule) == len(expected), "Duplicate (job, op) rows detected"

    allowed: Dict[Tuple[int, int], Dict[int, int]] = {}
    for job in range(jobs):
        for op in range(len(instance[job])):
            allowed[(job, op)] = {machine: duration for machine, duration in instance[job][op]}

    for row in schedule:
        key = (row["job"], row["op"])
        assert 0 <= row["machine"] < machines, f"Machine out of range for {key}: {row['machine']}"
        assert row["start"] >= 0, f"Negative start for {key}"
        assert row["dur"] > 0, f"Non-positive duration for {key}"
        assert row["end"] == row["start"] + row["dur"], f"end != start + dur for {key}"
        assert row["machine"] in allowed[key], f"Illegal machine choice for {key}"
        assert row["dur"] == allowed[key][row["machine"]], f"Duration mismatch for {key}"


def test_L1_precedence_constraints() -> None:
    _, _, instance = parse_instance(INSTANCE_PATH)
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    mapped = schedule_map(schedule)
    for job in range(len(instance)):
        for op in range(len(instance[job]) - 1):
            assert mapped[(job, op)]["end"] <= mapped[(job, op + 1)]["start"], f"Precedence violated for job {job} op{op}->{op + 1}"


def test_L1_no_machine_overlap_strict() -> None:
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    by_machine: Dict[int, List[Tuple[int, int, int, int]]] = {}
    for row in schedule:
        by_machine.setdefault(row["machine"], []).append((row["start"], row["end"], row["job"], row["op"]))
    for machine, intervals in by_machine.items():
        intervals.sort()
        for idx in range(len(intervals) - 1):
            assert intervals[idx][1] <= intervals[idx + 1][0], f"Machine overlap on machine {machine}: {intervals[idx]} vs {intervals[idx + 1]}"


def test_L1_makespan_matches_max_end() -> None:
    solution = load_json(SOLUTION_PATH)
    schedule = normalize_schedule(solution["schedule"])
    makespan = as_int(solution["makespan"])
    assert makespan == max(row["end"] for row in schedule), "Reported makespan does not match schedule"


def test_L2_no_downtime_violations_any_window() -> None:
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    downtime = load_downtime()
    assert count_downtime_violations(schedule, downtime) == 0, "Schedule overlaps downtime windows"


def test_L3_same_jobop_keys_as_baseline() -> None:
    baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    assert set(schedule_map(schedule).keys()) == set(schedule_map(baseline).keys()), "Must preserve exactly the baseline (job, op) set"


def test_L3_policy_budget_enforced() -> None:
    policy = get_policy()
    budget = get_change_budget(policy)
    baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    machine_changes, total_shift = change_metrics(schedule, baseline)
    assert machine_changes <= budget["max_machine_changes"], f"Machine changes over budget: {machine_changes} > {budget['max_machine_changes']}"
    assert total_shift <= budget["max_total_start_shift_L1"], f"Total start shift over budget: {total_shift} > {budget['max_total_start_shift_L1']}"


def test_L3_right_shift_only_baseline_repair() -> None:
    baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
    baseline_map = schedule_map(baseline)
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    for row in schedule:
        key = (row["job"], row["op"])
        assert row["start"] >= baseline_map[key]["start"], f"Right-shift violated for {key}"


def test_L3_freeze_respected_if_declared() -> None:
    freeze_until, freeze_fields = get_freeze_policy(get_policy())
    if freeze_until is None or not freeze_fields:
        return

    baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    baseline_map = schedule_map(baseline)
    schedule_map_new = schedule_map(schedule)

    for key, base_row in baseline_map.items():
        if base_row["start"] < freeze_until:
            patched_row = schedule_map_new[key]
            for field in freeze_fields:
                if field in ("job", "op"):
                    continue
                if field in base_row and field in patched_row:
                    assert patched_row[field] == base_row[field], f"Freeze violated for {key} field '{field}'"


def test_L3_must_improve_baseline_downtime_metric() -> None:
    downtime = load_downtime()
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    patched_violations = count_downtime_violations(schedule, downtime)
    assert patched_violations == 0

    if exists(BASELINE_METRICS_PATH):
        baseline_violations = as_int(load_json(BASELINE_METRICS_PATH)["baseline"]["downtime_violations"])
    else:
        baseline_violations = count_downtime_violations(
            normalize_schedule(load_json(BASELINE_PATH)["schedule"]),
            downtime,
        )

    assert baseline_violations > 0, "Baseline must have downtime violations"
    assert baseline_violations > patched_violations, "Patched schedule must improve downtime violations"


def test_L3_local_minimal_right_shift_in_precedence_aware_order() -> None:
    downtime = load_downtime()
    baseline = normalize_schedule(load_json(BASELINE_PATH)["schedule"])
    baseline_map = schedule_map(baseline)
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    patched_map = schedule_map(schedule)
    order = precedence_aware_repair_order(baseline)

    machine_intervals: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    job_end: Dict[int, int] = defaultdict(int)

    for key in order:
        base_row = baseline_map[key]
        patched_row = patched_map[key]
        job, _ = key
        anchor = max(base_row["start"], job_end[job])
        start = patched_row["start"]
        end = patched_row["end"]
        duration = patched_row["dur"]
        machine = patched_row["machine"]

        assert start >= anchor, f"Start earlier than anchor for {key}: start={start} anchor={anchor}"

        if start > anchor:
            candidate = start - 1
            assert conflicts_with_machine_or_downtime(
                machine,
                candidate,
                candidate + duration,
                machine_intervals,
                downtime,
            ), f"Not locally minimal for {key}: start={start} anchor={anchor}"

        machine_intervals[machine].append((start, end))
        machine_intervals[machine].sort()
        job_end[job] = end


def test_L4_csv_has_minimum_columns_and_parses() -> None:
    rows = load_csv(CSV_PATH)
    assert rows, "schedule.csv must not be empty"
    required = {"job", "op", "machine", "start", "end", "dur"}
    assert required.issubset(rows[0].keys()), f"schedule.csv must include columns {sorted(required)}"
    for row in rows:
        for key in required:
            _ = as_int(row[key])


def test_L4_csv_matches_solution_on_keys_and_times_unordered() -> None:
    schedule = normalize_schedule(load_json(SOLUTION_PATH)["schedule"])
    rows = load_csv(CSV_PATH)
    schedule_csv = [
        {
            "job": as_int(row["job"]),
            "op": as_int(row["op"]),
            "machine": as_int(row["machine"]),
            "start": as_int(row["start"]),
            "end": as_int(row["end"]),
            "dur": as_int(row["dur"]),
        }
        for row in rows
    ]
    assert set(map(tuple_key, schedule_csv)) == set(map(tuple_key, schedule)), "schedule.csv must match solution.json schedule"
