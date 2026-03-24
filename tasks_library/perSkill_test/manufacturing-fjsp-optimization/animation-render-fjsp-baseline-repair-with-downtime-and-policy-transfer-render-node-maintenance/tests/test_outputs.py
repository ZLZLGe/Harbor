import csv
import json
import os
from collections import defaultdict


APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA_DIR = os.environ.get("DATA_DIR", f"{APP_ROOT}/data")
OUT_DIR = os.environ.get("OUT_DIR", f"{APP_ROOT}/output")

MANIFEST_PATH = f"{DATA_DIR}/show_manifest.json"
WINDOWS_PATH = f"{DATA_DIR}/maintenance_windows.csv"
POLICY_PATH = f"{DATA_DIR}/recovery_policy.json"
BASELINE_PATH = f"{DATA_DIR}/baseline_render_queue.csv"
HEALTH_PATH = f"{DATA_DIR}/baseline_health.json"
OUTPUT_PATH = f"{OUT_DIR}/render_recovery_plan.json"


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
    stations = {
        str(row["station_id"]): str(row["station_name"])
        for row in raw["stations"]
    }
    shots = {
        str(row["shot_id"]): row
        for row in raw["shots"]
    }
    return stations, shots


def load_windows():
    windows = defaultdict(list)
    for row in load_csv(WINDOWS_PATH):
        windows[str(row["station_id"])].append((int(row["start"]), int(row["end"])))
    for station_id in windows:
        windows[station_id].sort()
    return windows


def normalize_plan(raw):
    assert raw["status"] == "READY_FOR_REVIEW"
    assert isinstance(raw["review_queue"], list)
    assert isinstance(raw["render_plan"], list)
    plan = []
    for row in raw["render_plan"]:
        plan.append(
            {
                "shot_id": str(row["shot_id"]),
                "stage": str(row["stage"]),
                "stage_index": int(row["stage_index"]),
                "station_id": str(row["station_id"]),
                "station_name": str(row["station_name"]),
                "start": int(row["start"]),
                "finish": int(row["finish"]),
                "duration": int(row["duration"]),
            }
        )
    return plan


def load_baseline():
    baseline = []
    for row in load_csv(BASELINE_PATH):
        baseline.append(
            {
                "shot_id": str(row["shot_id"]),
                "stage": str(row["stage"]),
                "stage_index": int(row["stage_index"]),
                "station_id": str(row["station_id"]),
                "station_name": str(row["station_name"]),
                "start": int(row["start"]),
                "finish": int(row["finish"]),
                "duration": int(row["duration"]),
            }
        )
    return baseline


def plan_map(plan):
    return {(row["shot_id"], row["stage_index"]): row for row in plan}


def change_metrics(plan, baseline):
    patched_map = plan_map(plan)
    baseline_map = plan_map(baseline)
    station_changes = sum(
        patched_map[key]["station_id"] != baseline_map[key]["station_id"]
        for key in baseline_map
    )
    total_shift = sum(
        abs(patched_map[key]["start"] - baseline_map[key]["start"])
        for key in baseline_map
    )
    return station_changes, total_shift


def count_maintenance_hits(plan, windows):
    hits = 0
    impacted = set()
    for row in plan:
        for left, right in windows.get(row["station_id"], []):
            if overlap(row["start"], row["finish"], left, right):
                hits += 1
                impacted.add(row["shot_id"])
                break
    return hits, impacted


def count_station_overlaps(plan):
    overlaps = 0
    by_station = defaultdict(list)
    for row in plan:
        by_station[row["station_id"]].append(
            (row["start"], row["finish"], row["shot_id"], row["stage_index"])
        )
    for station_id, intervals in by_station.items():
        intervals.sort()
        for left, right in zip(intervals, intervals[1:]):
            if left[1] > right[0]:
                overlaps += 1
    return overlaps


def shot_review_finish(plan):
    return {
        row["shot_id"]: row["finish"]
        for row in plan
        if row["stage_index"] == 3
    }


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), f"missing output: {OUTPUT_PATH}"


def test_schema_and_last_review():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    assert set(raw["budget_usage"]) == {"station_changes", "total_start_shift"}
    assert raw["last_review_minute"] == max(row["finish"] for row in plan)


def test_complete_shot_stage_set_and_allowed_stations():
    station_names, shots = load_manifest()
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)

    expected = {
        (shot_id, stage_index)
        for shot_id, shot in shots.items()
        for stage_index in range(len(shot["stages"]))
    }
    actual = {(row["shot_id"], row["stage_index"]) for row in plan}
    assert actual == expected
    assert len(plan) == len(expected)

    allowed = {}
    stage_names = {}
    for shot_id, shot in shots.items():
        for stage_index, stage in enumerate(shot["stages"]):
            allowed[(shot_id, stage_index)] = {
                str(option["station_id"]): int(option["duration"])
                for option in stage["options"]
            }
            stage_names[(shot_id, stage_index)] = str(stage["stage"])

    for row in plan:
        key = (row["shot_id"], row["stage_index"])
        assert row["station_id"] in allowed[key]
        assert row["duration"] == allowed[key][row["station_id"]]
        assert row["finish"] == row["start"] + row["duration"]
        assert row["start"] >= 0
        assert row["stage"] == stage_names[key]
        assert row["station_name"] == station_names[row["station_id"]]


def test_precedence_and_station_capacity():
    _, shots = load_manifest()
    plan = normalize_plan(load_json(OUTPUT_PATH))
    mapped = plan_map(plan)

    for shot_id, shot in shots.items():
        for stage_index in range(len(shot["stages"]) - 1):
            assert (
                mapped[(shot_id, stage_index)]["finish"]
                <= mapped[(shot_id, stage_index + 1)]["start"]
            )

    assert count_station_overlaps(plan) == 0


def test_no_maintenance_conflicts_and_right_shift_only():
    windows = load_windows()
    plan = normalize_plan(load_json(OUTPUT_PATH))
    baseline = load_baseline()
    baseline_map = plan_map(baseline)
    patched_map = plan_map(plan)

    assert count_maintenance_hits(plan, windows)[0] == 0
    for key, baseline_row in baseline_map.items():
        assert patched_map[key]["start"] >= baseline_row["start"]


def test_freeze_and_budget_usage():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    baseline = load_baseline()
    baseline_map = plan_map(baseline)
    patched_map = plan_map(plan)
    policy = load_json(POLICY_PATH)
    freeze_before = int(policy["freeze"]["before_minute"])
    freeze_fields = set(policy["freeze"]["fields"])

    station_changes, total_shift = change_metrics(plan, baseline)
    assert raw["budget_usage"]["station_changes"] == station_changes
    assert raw["budget_usage"]["total_start_shift"] == total_shift
    assert station_changes <= int(policy["change_budget"]["max_station_changes"])
    assert total_shift <= int(policy["change_budget"]["max_total_start_shift"])

    for key, baseline_row in baseline_map.items():
        patched_row = patched_map[key]
        if baseline_row["start"] < freeze_before:
            if "station_id" in freeze_fields:
                assert patched_row["station_id"] == baseline_row["station_id"]
            if "start" in freeze_fields:
                assert patched_row["start"] == baseline_row["start"]


def test_review_queue_deadlines_and_guardrails():
    raw = load_json(OUTPUT_PATH)
    plan = normalize_plan(raw)
    _, shots = load_manifest()
    guardrails = load_json(POLICY_PATH)["guards"]
    review_finish = shot_review_finish(plan)
    expected_queue = [
        shot_id
        for shot_id, _ in sorted(review_finish.items(), key=lambda item: (item[1], item[0]))
    ]
    late_shots = 0
    for shot_id, finish in review_finish.items():
        if finish > int(shots[shot_id]["review_due"]):
            late_shots += 1

    assert raw["review_queue"] == expected_queue
    assert raw["last_review_minute"] <= int(guardrails["max_last_review_minute"])
    assert late_shots <= int(guardrails["max_late_shots"])


def test_baseline_maintenance_problem_is_removed():
    windows = load_windows()
    health = load_json(HEALTH_PATH)
    baseline = load_baseline()
    repaired = normalize_plan(load_json(OUTPUT_PATH))

    baseline_hits, baseline_impacted = count_maintenance_hits(baseline, windows)
    repaired_hits, repaired_impacted = count_maintenance_hits(repaired, windows)

    assert baseline_hits == int(health["baseline"]["maintenance_hits"])
    assert sorted(baseline_impacted) == sorted(health["baseline"]["shots_touching_maintenance"])
    assert baseline_hits > 0
    assert repaired_hits == 0
    assert repaired_impacted == set()
