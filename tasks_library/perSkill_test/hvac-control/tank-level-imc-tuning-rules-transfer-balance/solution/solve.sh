#!/bin/bash
set -e

TASK_ROOT="${TASK_ROOT:-/root}"
OUTPUT_DIR="${OUTPUT_DIR:-$TASK_ROOT}"

python3 <<'PY'
import importlib.util
import json
import os
from pathlib import Path

task_root = Path(os.environ.get("TASK_ROOT", "/root"))
output_dir = Path(os.environ.get("OUTPUT_DIR", str(task_root)))

sim_path = task_root / "tank_level_sim.py"
case_path = task_root / "tank_level_case.json"
output_path = output_dir / "tank_level_controller_report.json"

spec = importlib.util.spec_from_file_location("tank_level_sim", sim_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with open(case_path, "r", encoding="utf-8") as f:
    scenario = json.load(f)

process_gain = scenario["process_gain_pct_per_valve_pct"]
tau = scenario["time_constant_s"]

lambda_s = round(0.45 * tau, 4)
kp = round(tau / (process_gain * lambda_s), 6)
ki = round(kp / tau, 6)

trace = module.simulate_pi_controller(str(case_path), kp, ki)
metrics = module.compute_metrics(
    trace,
    scenario["target_level_pct"],
    scenario["settling_band_pct"],
    scenario["steady_state_window_s"],
    scenario["dt_s"],
)

required_hold_valve_pct = round(module.required_hold_valve_pct(scenario), 4)
average_valve_pct_last_120s = module.average_valve_pct_last_window(
    trace,
    scenario["steady_state_window_s"],
    scenario["dt_s"],
)
outflow_rejection_ok = (
    metrics["settling_time_s"] <= 320.0
    and abs(average_valve_pct_last_120s - required_hold_valve_pct) <= 1.0
)

report = {
    "scenario": {
        "target_level_pct": scenario["target_level_pct"],
        "initial_level_pct": scenario["initial_level_pct"],
        "base_level_pct": scenario["base_level_pct"],
        "constant_outflow_equivalent_pct": scenario["constant_outflow_equivalent_pct"],
        "process_gain_pct_per_valve_pct": scenario["process_gain_pct_per_valve_pct"],
        "time_constant_s": scenario["time_constant_s"],
        "duration_s": scenario["duration_s"],
        "dt_s": scenario["dt_s"],
    },
    "controller": {
        "type": "PI",
        "Kp": kp,
        "Ki": ki,
        "Kd": 0.0,
        "lambda_s": lambda_s,
    },
    "checkpoints": module.build_checkpoints(trace, [60, 120, 240, 360, 540, 720]),
    "performance_summary": metrics,
    "balance_analysis": {
        "required_hold_valve_pct": required_hold_valve_pct,
        "average_valve_pct_last_120s": average_valve_pct_last_120s,
        "outflow_rejection_ok": outflow_rejection_ok,
    },
    "assessment": "The tank level rises smoothly to the target and holds the balance point against the constant draw.",
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY
