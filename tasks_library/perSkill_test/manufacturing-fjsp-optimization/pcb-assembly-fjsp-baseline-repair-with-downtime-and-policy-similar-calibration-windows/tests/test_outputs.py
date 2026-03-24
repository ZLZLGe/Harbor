import json
import os
from collections import defaultdict


OUT_PATH = "/app/output/pcb_repair_plan.json"
DATA_DIR = "/app/data"
ROUTES_PATH = f"{DATA_DIR}/board_routes.txt"
WINDOWS_PATH = f"{DATA_DIR}/calibration_windows.csv"
POLICY_PATH = f"{DATA_DIR}/repair_policy.json"
BASELINE_PATH = f"{DATA_DIR}/baseline_plan.json"
SNAPSHOT_PATH = f"{DATA_DIR}/baseline_snapshot.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_routes(path):
    tokens = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                tokens.extend(stripped.split())
    it = iter(tokens)
    lots = int(next(it))
    lines = int(next(it))
    routes = []
    for _ in range(lots):
        stage_count = int(next(it))
        stages = []
        for _ in range(stage_count):
            option_count = int(next(it))
            options = []
            for _ in range(option_count):
                line_id = int(next(it))
                duration = int(next(it))
                options.append((line_id, duration))
            stages.append(options)
        routes.append(stages)
    return lots, lines, routes


def load_windows(path):
    windows = defaultdict(list)
    with open(path, "r", encoding="utf-8") as f:
        header = next(f)
        assert header.strip() == "line,start,end,reason"
        for raw in f:
            line_id, start, end, _ = raw.strip().split(",", 3)
            windows[int(line_id)].append((int(start), int(end)))
    for line_id in windows:
        windows[line_id].sort()
    return windows


def normalize_plan(raw):
    assert isinstance(raw, dict)
    assert isinstance(raw.get("line_plan"), list)
    plan = []
    for row in raw["line_plan"]:
        plan.append(
            {
                "lot": int(row["lot"]),
                "stage": int(row["stage"]),
                "line": int(row["line"]),
                "start": int(row["start"]),
                "finish": int(row["finish"]),
                "duration": int(row["duration"]),
            }
        )
    return plan


def plan_map(plan):
    return {(row["lot"], row["stage"]): row for row in plan}


def overlap(a, b, c, d):
    return a < d and c < b


def count_calibration_conflicts(plan, windows):
    count = 0
    for row in plan:
        for left, right in windows.get(row["line"], []):
            if overlap(row["start"], row["finish"], left, right):
                count += 1
                break
    return count


def count_precedence_violations(plan, routes):
    mapped = plan_map(plan)
    violations = 0
    for lot, stages in enumerate(routes):
        for stage in range(len(stages) - 1):
            if mapped[(lot, stage)]["finish"] > mapped[(lot, stage + 1)]["start"]:
                violations += 1
    return violations


def change_metrics(plan, baseline):
    patched_map = plan_map(plan)
    baseline_map = plan_map(baseline)
    line_changes = sum(patched_map[key]["line"] != baseline_map[key]["line"] for key in baseline_map)
    total_start_shift = sum(abs(patched_map[key]["start"] - baseline_map[key]["start"]) for key in baseline_map)
    return line_changes, total_start_shift


def precedence_order(plan):
    mapped = plan_map(plan)
    baseline_index = {(row["lot"], row["stage"]): idx for idx, row in enumerate(plan)}
    keys = [(row["lot"], row["stage"]) for row in plan]
    keys.sort(key=lambda key: (key[1], mapped[key]["start"], baseline_index[key]))
    return keys


def conflicts_with_line_or_window(line_id, start, finish, line_intervals, windows):
    for left, right in line_intervals.get(line_id, []):
        if overlap(start, finish, left, right):
            return True
    for left, right in windows.get(line_id, []):
        if overlap(start, finish, left, right):
            return True
    return False


def load_policy():
    return load_json(POLICY_PATH)


def get_freeze(policy):
    freeze = policy.get("freeze", {})
    until = freeze.get("until")
    fields = freeze.get("fields", [])
    return (int(until) if until is not None else None), [str(field) for field in fields]


def get_budget(policy):
    budget = policy.get("change_budget", {})
    return int(budget.get("max_machine_changes", 10**9)), int(budget.get("max_total_start_shift_L1", 10**18))


def test_output_exists():
    assert os.path.exists(OUT_PATH), f"missing output: {OUT_PATH}"


def test_output_schema():
    raw = load_json(OUT_PATH)
    assert raw["status"] == "REPAIRED"
    assert isinstance(int(raw["completion_time"]), int)
    assert isinstance(raw["change_budget_usage"], dict)
    assert set(raw["change_budget_usage"]) == {"line_changes", "total_start_shift"}
    normalize_plan(raw)


def test_complete_lot_stage_set_and_allowed_lines():
    lot_count, line_count, routes = parse_routes(ROUTES_PATH)
    raw = load_json(OUT_PATH)
    plan = normalize_plan(raw)
    expected = {(lot, stage) for lot in range(lot_count) for stage in range(len(routes[lot]))}
    actual = {(row["lot"], row["stage"]) for row in plan}
    assert actual == expected
    assert len(plan) == len(expected)

    allowed = {}
    for lot in range(lot_count):
        for stage in range(len(routes[lot])):
            allowed[(lot, stage)] = {line_id: duration for line_id, duration in routes[lot][stage]}

    for row in plan:
        key = (row["lot"], row["stage"])
        assert 0 <= row["line"] < line_count
        assert row["line"] in allowed[key]
        assert row["duration"] == allowed[key][row["line"]]
        assert row["start"] >= 0
        assert row["finish"] == row["start"] + row["duration"]


def test_precedence_and_line_capacity():
    _, _, routes = parse_routes(ROUTES_PATH)
    raw = load_json(OUT_PATH)
    plan = normalize_plan(raw)
    mapped = plan_map(plan)
    for lot, stages in enumerate(routes):
        for stage in range(len(stages) - 1):
            assert mapped[(lot, stage)]["finish"] <= mapped[(lot, stage + 1)]["start"]

    by_line = defaultdict(list)
    for row in plan:
        by_line[row["line"]].append((row["start"], row["finish"], row["lot"], row["stage"]))
    for line_id, intervals in by_line.items():
        intervals.sort()
        for idx in range(len(intervals) - 1):
            assert intervals[idx][1] <= intervals[idx + 1][0], f"line overlap on {line_id}"


def test_completion_time_and_windows():
    raw = load_json(OUT_PATH)
    plan = normalize_plan(raw)
    windows = load_windows(WINDOWS_PATH)
    assert raw["completion_time"] == max(row["finish"] for row in plan)
    assert count_calibration_conflicts(plan, windows) == 0


def test_budget_usage_matches_plan_and_policy():
    policy = load_policy()
    max_line_changes, max_total_shift = get_budget(policy)
    raw = load_json(OUT_PATH)
    plan = normalize_plan(raw)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    line_changes, total_start_shift = change_metrics(plan, baseline)

    usage = raw["change_budget_usage"]
    assert usage["line_changes"] == line_changes
    assert usage["total_start_shift"] == total_start_shift
    assert line_changes <= max_line_changes
    assert total_start_shift <= max_total_shift


def test_right_shift_only_and_freeze_respected():
    policy = load_policy()
    until, fields = get_freeze(policy)
    raw = load_json(OUT_PATH)
    plan = normalize_plan(raw)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    patched_map = plan_map(plan)
    baseline_map = plan_map(baseline)

    for key, base_row in baseline_map.items():
        patched_row = patched_map[key]
        assert patched_row["start"] >= base_row["start"]
        if until is not None and base_row["start"] < until:
            if "line" in fields:
                assert patched_row["line"] == base_row["line"]
            if "start" in fields:
                assert patched_row["start"] == base_row["start"]


def test_baseline_is_improved_on_named_conflicts():
    snapshot = load_json(SNAPSHOT_PATH)
    _, _, routes = parse_routes(ROUTES_PATH)
    windows = load_windows(WINDOWS_PATH)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    plan = normalize_plan(load_json(OUT_PATH))

    baseline_conflicts = count_calibration_conflicts(baseline, windows)
    baseline_precedence = count_precedence_violations(baseline, routes)
    assert baseline_conflicts == snapshot["baseline"]["calibration_conflicts"]
    assert baseline_precedence == snapshot["baseline"]["precedence_violations"]
    assert baseline_conflicts > 0
    assert baseline_precedence > 0
    assert count_calibration_conflicts(plan, windows) == 0
    assert count_precedence_violations(plan, routes) == 0


def test_precedence_aware_local_minimality():
    _, _, routes = parse_routes(ROUTES_PATH)
    windows = load_windows(WINDOWS_PATH)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    plan = normalize_plan(load_json(OUT_PATH))
    baseline_map = plan_map(baseline)
    patched_map = plan_map(plan)
    order = precedence_order(baseline)

    line_intervals = defaultdict(list)
    lot_finish = defaultdict(int)

    for key in order:
        lot, stage = key
        base_row = baseline_map[key]
        patched_row = patched_map[key]
        anchor = max(base_row["start"], lot_finish[lot])
        assert patched_row["start"] >= anchor
        if patched_row["start"] > anchor:
            candidate = patched_row["start"] - 1
            assert conflicts_with_line_or_window(
                patched_row["line"],
                candidate,
                candidate + patched_row["duration"],
                line_intervals,
                windows,
            )
        line_intervals[patched_row["line"]].append((patched_row["start"], patched_row["finish"]))
        line_intervals[patched_row["line"]].sort()
        lot_finish[lot] = patched_row["finish"]


def test_guarded_completion_time():
    policy = load_policy()
    guard = policy.get("guards", {}).get("max_completion_time")
    if guard is None:
        return
    raw = load_json(OUT_PATH)
    assert raw["completion_time"] <= int(guard)
