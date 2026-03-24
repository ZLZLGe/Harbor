import csv
import json
import os
from collections import defaultdict


APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA_DIR = os.environ.get("DATA_DIR", f"{APP_ROOT}/data")
OUT_DIR = os.environ.get("OUT_DIR", f"{APP_ROOT}/output")

ROUTES_PATH = f"{DATA_DIR}/tray_routes.json"
DOWNTIME_PATH = f"{DATA_DIR}/unit_downtime.csv"
POLICY_PATH = f"{DATA_DIR}/repair_policy.json"
BASELINE_PATH = f"{DATA_DIR}/baseline_cssd_plan.json"
ISSUES_PATH = f"{DATA_DIR}/baseline_issues.json"
OUTPUT_PATH = f"{OUT_DIR}/cssd_day_plan.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def overlap(a, b, c, d):
    return a < d and c < b


def load_routes():
    raw = load_json(ROUTES_PATH)
    units = {int(row["unit_id"]): str(row["unit_name"]) for row in raw["units"]}
    trays = raw["trays"]
    return units, trays


def load_downtime():
    windows = defaultdict(list)
    for row in load_csv(DOWNTIME_PATH):
        unit_id = int(row["unit_id"])
        windows[unit_id].append((int(row["start"]), int(row["end"])))
    for unit_id in windows:
        windows[unit_id].sort()
    return windows


def normalize_plan(raw):
    assert isinstance(raw["ready_trays"], list)
    assert isinstance(raw["tray_plan"], list)
    plan = []
    for row in raw["tray_plan"]:
        plan.append(
            {
                "tray_id": str(row["tray_id"]),
                "step": str(row["step"]),
                "step_index": int(row["step_index"]),
                "unit_id": int(row["unit_id"]),
                "unit_name": str(row["unit_name"]),
                "start": int(row["start"]),
                "finish": int(row["finish"]),
                "duration": int(row["duration"]),
            }
        )
    return plan


def plan_map(plan):
    return {(row["tray_id"], row["step_index"]): row for row in plan}


def count_outage_conflicts(plan, downtime):
    count = 0
    for row in plan:
        for left, right in downtime.get(row["unit_id"], []):
            if overlap(row["start"], row["finish"], left, right):
                count += 1
                break
    return count


def count_unit_overlaps(plan):
    overlaps = 0
    by_unit = defaultdict(list)
    for row in plan:
        by_unit[row["unit_id"]].append((row["start"], row["finish"], row["tray_id"], row["step_index"]))
    for unit_id, intervals in by_unit.items():
        intervals.sort()
        for left, right in zip(intervals, intervals[1:]):
            if left[1] > right[0]:
                overlaps += 1
    return overlaps


def change_metrics(plan, baseline):
    patched_map = plan_map(plan)
    baseline_map = plan_map(baseline)
    unit_changes = sum(
        patched_map[key]["unit_id"] != baseline_map[key]["unit_id"]
        for key in baseline_map
    )
    total_shift = sum(
        abs(patched_map[key]["start"] - baseline_map[key]["start"])
        for key in baseline_map
    )
    return unit_changes, total_shift


def tray_final_finish(plan):
    last_finish = {}
    for row in plan:
        if row["step_index"] == 2:
            last_finish[row["tray_id"]] = row["finish"]
    return last_finish


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), f"missing output: {OUTPUT_PATH}"


def test_schema_and_last_ready():
    raw = load_json(OUTPUT_PATH)
    assert raw["status"] == "DAY_PLAN_READY"
    plan = normalize_plan(raw)
    assert set(raw["budget_usage"]) == {"unit_changes", "total_start_shift"}
    assert raw["last_ready_minute"] == max(row["finish"] for row in plan)


def test_complete_tray_step_set_and_allowed_units():
    unit_names, trays = load_routes()
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    expected = {
        (tray["tray_id"], step_index)
        for tray in trays
        for step_index in range(len(tray["steps"]))
    }
    actual = {(row["tray_id"], row["step_index"]) for row in plan}
    assert actual == expected
    assert len(plan) == len(expected)

    allowed = {}
    step_names = {}
    for tray in trays:
        for step_index, step in enumerate(tray["steps"]):
            allowed[(tray["tray_id"], step_index)] = {
                int(option["unit_id"]): int(option["duration"])
                for option in step["options"]
            }
            step_names[(tray["tray_id"], step_index)] = str(step["step"])

    for row in plan:
        key = (row["tray_id"], row["step_index"])
        assert row["unit_id"] in allowed[key]
        assert row["duration"] == allowed[key][row["unit_id"]]
        assert row["finish"] == row["start"] + row["duration"]
        assert row["start"] >= 0
        assert row["step"] == step_names[key]
        assert row["unit_name"] == unit_names[row["unit_id"]]


def test_precedence_and_unit_capacity():
    _, trays = load_routes()
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    mapped = plan_map(plan)

    for tray in trays:
        tray_id = tray["tray_id"]
        for step_index in range(len(tray["steps"]) - 1):
            assert (
                mapped[(tray_id, step_index)]["finish"]
                <= mapped[(tray_id, step_index + 1)]["start"]
            )

    assert count_unit_overlaps(plan) == 0


def test_outages_and_budget_usage():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    policy = load_json(POLICY_PATH)
    downtime = load_downtime()

    unit_changes, total_shift = change_metrics(plan, baseline)
    assert raw["budget_usage"]["unit_changes"] == unit_changes
    assert raw["budget_usage"]["total_start_shift"] == total_shift
    assert unit_changes <= int(policy["change_budget"]["max_machine_changes"])
    assert total_shift <= int(policy["change_budget"]["max_total_start_shift_L1"])
    assert count_outage_conflicts(plan, downtime) == 0


def test_right_shift_freeze_and_deadlines():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    baseline_map = plan_map(baseline)
    patched_map = plan_map(plan)
    policy = load_json(POLICY_PATH)
    freeze_until = int(policy["freeze"]["until"])
    freeze_fields = set(policy["freeze"]["fields"])
    _, trays = load_routes()
    deadlines = {tray["tray_id"]: int(tray["release_deadline"]) for tray in trays}

    for key, baseline_row in baseline_map.items():
        patched_row = patched_map[key]
        assert patched_row["start"] >= baseline_row["start"]
        if baseline_row["start"] < freeze_until:
            if "unit_id" in freeze_fields:
                assert patched_row["unit_id"] == baseline_row["unit_id"]
            if "start" in freeze_fields:
                assert patched_row["start"] == baseline_row["start"]

    for tray_id, finish in tray_final_finish(plan).items():
        assert finish <= deadlines[tray_id]


def test_ready_order_and_guardrails():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    guardrails = load_json(POLICY_PATH)["guards"]
    final_finish = tray_final_finish(plan)
    expected_ready = [
        tray_id
        for tray_id, _ in sorted(final_finish.items(), key=lambda item: (item[1], item[0]))
    ]
    missed_deadlines = 0
    _, trays = load_routes()
    deadlines = {tray["tray_id"]: int(tray["release_deadline"]) for tray in trays}
    for tray_id, finish in final_finish.items():
        if finish > deadlines[tray_id]:
            missed_deadlines += 1

    assert raw["ready_trays"] == expected_ready
    assert raw["last_ready_minute"] <= int(guardrails["max_last_ready_minute"])
    assert missed_deadlines <= int(guardrails["max_missed_deadlines"])


def test_baseline_problem_is_removed():
    issues = load_json(ISSUES_PATH)
    downtime = load_downtime()
    baseline = normalize_plan(load_json(BASELINE_PATH))
    repaired = normalize_plan(load_json(OUTPUT_PATH))

    assert count_outage_conflicts(baseline, downtime) == issues["baseline"]["outage_conflicts"]
    assert count_unit_overlaps(baseline) == issues["baseline"]["unit_overlaps"]
    assert issues["baseline"]["outage_conflicts"] > 0
    assert issues["baseline"]["unit_overlaps"] > 0
    assert count_outage_conflicts(repaired, downtime) == 0
    assert count_unit_overlaps(repaired) == 0
