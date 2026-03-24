#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TASK_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

if [ -n "${TASK_ROOT:-}" ] && [ -f "$TASK_ROOT/brine_mixer_case.json" ] && [ -f "$TASK_ROOT/brine_mixer_sim.py" ]; then
  CASE_PATH="$TASK_ROOT/brine_mixer_case.json"
  SIM_PATH="$TASK_ROOT/brine_mixer_sim.py"
  OUTPUT_PATH="$TASK_ROOT/brine_mixer_control_summary.json"
elif [ -f /root/brine_mixer_case.json ] && [ -f /root/brine_mixer_sim.py ]; then
  CASE_PATH=/root/brine_mixer_case.json
  SIM_PATH=/root/brine_mixer_sim.py
  OUTPUT_PATH=/root/brine_mixer_control_summary.json
else
  CASE_PATH="$TASK_DIR/environment/brine_mixer_case.json"
  SIM_PATH="$TASK_DIR/environment/brine_mixer_sim.py"
  OUTPUT_PATH="$TASK_DIR/brine_mixer_control_summary.json"
fi

python3 - "$CASE_PATH" "$SIM_PATH" "$OUTPUT_PATH" <<'PY'
import importlib.util
import json
import sys


case_path, sim_path, output_path = sys.argv[1:4]

spec = importlib.util.spec_from_file_location("brine_mixer_sim", sim_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

case = module.load_case(case_path)
lambda_s = 35.0
kp = case["time_constant_s"] / (
    case["process_gain_pct_per_valve_pct"] * lambda_s
)
ki = kp / case["time_constant_s"]
kp = module.round_float(kp)
ki = module.round_float(ki)

trace = module.simulate_pi_controller(case_path, kp, ki)
sampled_response = module.build_sampled_response(trace, case["sample_times_s"])
phase_summary = module.compute_phase_summary(trace, case)

result = {
    "scenario": {
        "target_concentration_pct": case["target_concentration_pct"],
        "initial_concentration_pct": case["initial_concentration_pct"],
        "base_concentration_pct": case["base_concentration_pct"],
        "nominal_brine_valve_pct": case["nominal_brine_valve_pct"],
        "process_gain_pct_per_valve_pct": case["process_gain_pct_per_valve_pct"],
        "time_constant_s": case["time_constant_s"],
        "duration_s": case["duration_s"],
        "dt_s": case["dt_s"],
    },
    "mixing_event": {
        "flush_start_s": case["flush_start_s"],
        "flush_end_s": case["flush_end_s"],
        "dilution_shift_pct": case["dilution_shift_pct"],
    },
    "controller": {
        "type": "PI",
        "Kp": kp,
        "Ki": ki,
        "Kd": 0.0,
        "lambda_s": module.round_float(lambda_s),
        "bias_valve_pct": case["nominal_brine_valve_pct"],
    },
    "sampled_response": sampled_response,
    "phase_summary": phase_summary,
    "blend_assessment": (
        "The controller corrects the lean start, limits the flush dip, "
        "and returns the mixer close to the recipe target."
    ),
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
