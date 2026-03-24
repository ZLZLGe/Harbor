import csv
import json
import os
from collections import defaultdict


APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA_DIR = os.environ.get("DATA_DIR", f"{APP_ROOT}/data")
OUT_DIR = os.environ.get("OUT_DIR", f"{APP_ROOT}/output")

MANIFEST_PATH = f"{DATA_DIR}/flight_service_manifest.json"
WINDOWS_PATH = f"{DATA_DIR}/equipment_maintenance.csv"
POLICY_PATH = f"{DATA_DIR}/repair_policy.json"
BASELINE_PATH = f"{DATA_DIR}/baseline_catering_plan.json"
RISK_PATH = f"{DATA_DIR}/baseline_risk_report.csv"
OUTPUT_PATH = f"{OUT_DIR}/catering_shift_plan.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def overlap(a, b, c, d):
    return a < d and c < b


def load_manifest():
    raw = load_json(MANIFEST_PATH)
    equipment = {
        str(row["equipment_id"]): {
            "equipment_name": str(row["equipment_name"]),
            "group": str(row["group"]),
        }
        for row in raw["equipment"]
    }
    flights = {
        str(row["flight_id"]): row
        for row in raw["flights"]
    }
    return equipment, flights


def load_windows():
    windows = defaultdict(list)
    for row in load_csv(WINDOWS_PATH):
        windows[str(row["equipment_id"])].append((int(row["start"]), int(row["end"])))
    for equipment_id in windows:
        windows[equipment_id].sort()
    return windows


def normalize_plan(raw):
    assert isinstance(raw["dispatch_board"], list)
    assert isinstance(raw["kitchen_plan"], list)
    plan = []
    for row in raw["kitchen_plan"]:
        plan.append(
            {
                "flight_id": str(row["flight_id"]),
                "stage": str(row["stage"]),
                "stage_index": int(row["stage_index"]),
                "equipment_group": str(row["equipment_group"]),
                "equipment_id": str(row["equipment_id"]),
                "equipment_name": str(row["equipment_name"]),
                "start": int(row["start"]),
                "finish": int(row["finish"]),
                "duration": int(row["duration"]),
            }
        )
    return plan


def plan_map(plan):
    return {(row["flight_id"], row["stage_index"]): row for row in plan}


def count_maintenance_conflicts(plan, windows):
    count = 0
    for row in plan:
        for left, right in windows.get(row["equipment_id"], []):
            if overlap(row["start"], row["finish"], left, right):
                count += 1
                break
    return count


def count_equipment_overlaps(plan):
    count = 0
    by_equipment = defaultdict(list)
    for row in plan:
        by_equipment[row["equipment_id"]].append(
            (row["start"], row["finish"], row["flight_id"], row["stage_index"])
        )
    for equipment_id, intervals in by_equipment.items():
        intervals.sort()
        for left, right in zip(intervals, intervals[1:]):
            if left[1] > right[0]:
                count += 1
    return count


def load_risk_metrics():
    metrics = {}
    for row in load_csv(RISK_PATH):
        metrics[str(row["metric"])] = int(row["value"])
    return metrics


def change_metrics(plan, baseline):
    patched_map = plan_map(plan)
    baseline_map = plan_map(baseline)
    equipment_changes = sum(
        patched_map[key]["equipment_id"] != baseline_map[key]["equipment_id"]
        for key in baseline_map
    )
    total_shift = sum(
        abs(patched_map[key]["start"] - baseline_map[key]["start"])
        for key in baseline_map
    )
    return equipment_changes, total_shift


def final_ready_times(plan, flights):
    ready = {}
    for flight_id, flight in flights.items():
        last_stage_index = len(flight["stages"]) - 1
        ready[flight_id] = plan_map(plan)[(flight_id, last_stage_index)]["finish"]
    return ready


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), f"missing output: {OUTPUT_PATH}"


def test_schema_and_last_ready():
    raw = load_json(OUTPUT_PATH)
    assert raw["status"] == "DISPATCHABLE"
    plan = normalize_plan(raw)
    assert set(raw["budget_usage"]) == {"equipment_changes", "total_start_shift"}
    assert raw["last_ready_minute"] == max(row["finish"] for row in plan)


def test_complete_flight_stage_set_and_allowed_equipment():
    equipment, flights = load_manifest()
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)

    expected = {
        (flight_id, stage_index)
        for flight_id, flight in flights.items()
        for stage_index in range(len(flight["stages"]))
    }
    actual = {(row["flight_id"], row["stage_index"]) for row in plan}
    assert actual == expected
    assert len(plan) == len(expected)

    allowed = {}
    stage_names = {}
    stage_groups = {}
    for flight_id, flight in flights.items():
        for stage_index, stage in enumerate(flight["stages"]):
            allowed[(flight_id, stage_index)] = {
                str(option["equipment_id"]): int(option["duration"])
                for option in stage["options"]
            }
            stage_names[(flight_id, stage_index)] = str(stage["stage"])
            stage_groups[(flight_id, stage_index)] = str(stage["group"])

    for row in plan:
        key = (row["flight_id"], row["stage_index"])
        assert row["equipment_id"] in allowed[key]
        assert row["duration"] == allowed[key][row["equipment_id"]]
        assert row["finish"] == row["start"] + row["duration"]
        assert row["start"] >= 0
        assert row["stage"] == stage_names[key]
        assert row["equipment_group"] == stage_groups[key]
        assert row["equipment_name"] == equipment[row["equipment_id"]]["equipment_name"]
        assert row["equipment_group"] == equipment[row["equipment_id"]]["group"]


def test_precedence_and_equipment_capacity():
    _, flights = load_manifest()
    plan = normalize_plan(load_json(OUTPUT_PATH))
    mapped = plan_map(plan)

    for flight_id, flight in flights.items():
        for stage_index in range(len(flight["stages"]) - 1):
            assert (
                mapped[(flight_id, stage_index)]["finish"]
                <= mapped[(flight_id, stage_index + 1)]["start"]
            )

    assert count_equipment_overlaps(plan) == 0


def test_no_maintenance_conflicts():
    plan = normalize_plan(load_json(OUTPUT_PATH))
    windows = load_windows()
    assert count_maintenance_conflicts(plan, windows) == 0


def test_right_shift_freeze_and_budget():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    baseline_map = plan_map(baseline)
    patched_map = plan_map(plan)
    policy = load_json(POLICY_PATH)
    freeze_before = int(policy["freeze"]["before_minute"])
    freeze_fields = set(policy["freeze"]["fields"])
    max_changes = int(policy["change_budget"]["max_equipment_changes"])
    max_total_shift = int(policy["change_budget"]["max_total_start_shift"])

    equipment_changes, total_shift = change_metrics(plan, baseline)
    assert raw["budget_usage"]["equipment_changes"] == equipment_changes
    assert raw["budget_usage"]["total_start_shift"] == total_shift
    assert equipment_changes <= max_changes
    assert total_shift <= max_total_shift

    for key, baseline_row in baseline_map.items():
        patched_row = patched_map[key]
        assert patched_row["start"] >= baseline_row["start"]
        if baseline_row["start"] < freeze_before:
            if "equipment_id" in freeze_fields:
                assert patched_row["equipment_id"] == baseline_row["equipment_id"]
            if "start" in freeze_fields:
                assert patched_row["start"] == baseline_row["start"]


def test_dispatch_board_and_departure_buffers():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    _, flights = load_manifest()
    ready_times = final_ready_times(plan, flights)
    expected_board = []
    late_flights = 0

    for flight_id, flight in flights.items():
        ready_minute = ready_times[flight_id]
        departure_minute = int(flight["departure_minute"])
        buffer_to_departure = departure_minute - ready_minute
        if ready_minute > departure_minute - int(flight["ready_buffer"]):
            late_flights += 1
        expected_board.append(
            {
                "flight_id": flight_id,
                "ready_minute": ready_minute,
                "departure_minute": departure_minute,
                "buffer_to_departure": buffer_to_departure,
            }
        )

    expected_board.sort(key=lambda row: (row["departure_minute"], row["flight_id"]))
    assert raw["dispatch_board"] == expected_board
    assert late_flights <= int(load_json(POLICY_PATH)["guards"]["max_late_flights"])


def test_guardrails_and_baseline_risks():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    baseline = normalize_plan(load_json(BASELINE_PATH))
    windows = load_windows()
    metrics = load_risk_metrics()
    repaired_ready = final_ready_times(plan, load_manifest()[1])

    assert count_maintenance_conflicts(baseline, windows) == metrics["maintenance_conflicts"]
    assert count_equipment_overlaps(baseline) == metrics["equipment_overlaps"]
    assert metrics["maintenance_conflicts"] > 0
    assert metrics["equipment_overlaps"] > 0
    assert count_maintenance_conflicts(plan, windows) == 0
    assert count_equipment_overlaps(plan) == 0
    assert raw["last_ready_minute"] <= int(load_json(POLICY_PATH)["guards"]["max_last_ready_minute"])
    assert sum(
        ready > int(load_manifest()[1][flight_id]["departure_minute"]) - int(load_manifest()[1][flight_id]["ready_buffer"])
        for flight_id, ready in repaired_ready.items()
    ) == 0
