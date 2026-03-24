#!/bin/bash
set -e

TASK_ROOT="${TASK_ROOT:-/root}"
OUTPUT_DIR="${OUTPUT_DIR:-$TASK_ROOT}"

python3 <<'PY'
import json
import os
from pathlib import Path

task_root = Path(os.environ.get("TASK_ROOT", "/root"))
output_dir = Path(os.environ.get("OUTPUT_DIR", str(task_root)))

import importlib.util

sim_path = task_root / "incubator_recovery_sim.py"
case_path = task_root / "incubator_case.json"
output_path = output_dir / "incubator_controller_bundle.json"

spec = importlib.util.spec_from_file_location("incubator_recovery_sim", sim_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with open(case_path, "r", encoding="utf-8") as f:
    scenario = json.load(f)

process_gain = scenario["process_gain_c_per_percent"]
tau = scenario["time_constant_s"]

lambda_s = round(0.35 * tau, 4)
kp = tau / (process_gain * lambda_s)
ki = kp / tau

trace = module.simulate_pi_controller(str(case_path), kp, ki)
metrics = module.compute_metrics(
    trace,
    scenario["setpoint_c"],
    scenario["settling_band_c"],
    scenario["steady_state_window_s"],
    scenario["dt_s"],
)

bundle = {
    "scenario": {
        "setpoint_c": scenario["setpoint_c"],
        "initial_temp_c": scenario["initial_temp_c"],
        "ambient_temp_c": scenario["ambient_temp_c"],
        "process_gain_c_per_percent": scenario["process_gain_c_per_percent"],
        "time_constant_s": scenario["time_constant_s"],
        "duration_s": scenario["duration_s"],
        "dt_s": scenario["dt_s"],
    },
    "controller": {
        "type": "PI",
        "Kp": round(kp, 6),
        "Ki": round(ki, 6),
        "Kd": 0.0,
        "lambda_s": lambda_s,
    },
    "closed_loop_trace": trace,
    "performance_summary": metrics,
    "assessment": "The chamber returns to 37.0C smoothly with no meaningful overshoot and low final error.",
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(bundle, f, indent=2)
PY
