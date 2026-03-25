#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"

python3 - <<'PY'
import importlib.util
import json
import os
from pathlib import Path


root = Path(os.environ.get("TASK_ROOT", "/root"))
case_path = root / "surge_tank_case.json"
schedule_path = root / "disturbance_schedule.csv"
simulator_path = root / "surge_tank_simulator.py"
output_path = root / "surge_tank_level_report.json"


def load_module(path):
    spec = importlib.util.spec_from_file_location("surge_tank_simulator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sim = load_module(simulator_path)
case_data = sim.load_case(case_path)
schedule = sim.load_schedule(schedule_path)
evaluations = sim.evaluate_candidates(case_data, schedule)

feasible = [item for item in evaluations if item["meets_constraints"]]
if not feasible:
    raise RuntimeError("case data should provide at least one feasible lambda")

selected = max(feasible, key=lambda item: item["lambda_min"])
selected_lambda = selected["lambda_min"]
trajectory = sim.run_closed_loop(case_data, schedule, selected_lambda)
selected_metrics = sim.summarize_trajectory(case_data, schedule, trajectory)
acceptance = case_data["acceptance"]
clear_time = sim.disturbance_clear_time(schedule)

report = {
    "case_id": case_data["case_id"],
    "selection_rule": (
        "Evaluate every candidate lambda against the recovery deadline and rebound limit, "
        "then choose the largest lambda that satisfies all acceptance thresholds."
    ),
    "process_model": case_data["process_model"],
    "selected_lambda_min": selected_lambda,
    "controller": sim.controller_from_lambda(case_data, selected_lambda),
    "selected_metrics": selected_metrics,
    "candidate_review": evaluations,
    "recovery_trace": trajectory,
    "stability_report": {
        "disturbance_clear_time_min": clear_time,
        "within_band_at_end": abs(selected_metrics["final_error_percent"]) <= acceptance["stability_band_percent"],
        "meets_recovery_deadline": (
            selected_metrics["recovery_time_min"] is not None
            and selected_metrics["recovery_time_min"] <= acceptance["max_recovery_time_after_disturbance_min"]
        ),
        "meets_rebound_limit": (
            selected_metrics["peak_rebound_above_setpoint_percent"]
            <= acceptance["max_rebound_above_setpoint_percent"]
        ),
        "narrative": (
            f"Selected lambda {selected_lambda} min because it is the slowest candidate that still recovers "
            f"within {acceptance['max_recovery_time_after_disturbance_min']} min and keeps rebound within "
            f"{acceptance['max_rebound_above_setpoint_percent']} level percent."
        ),
    },
    "summary": (
        f"Lambda {selected_lambda} min is the most conservative feasible choice: slower candidates miss the "
        f"recovery target, while this one still restores the tank after the feed disturbance without a visible rebound."
    ),
}

with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
    handle.write("\n")
PY
