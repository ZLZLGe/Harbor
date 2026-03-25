#!/bin/bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f /root/coating_line_env.py ]; then
  export PYTHONPATH="/root:${PYTHONPATH:-}"
  cd /root
else
  export PYTHONPATH="$TASK_ROOT/environment:${PYTHONPATH:-}"
  cd "$TASK_ROOT"
fi

python3 <<'PY'
import json
from pathlib import Path

import numpy as np

from coating_line_env import summarize_trace
from controller_scaffold import NominalPredictiveController, run_baseline_case, run_case


class RetrofittedController(NominalPredictiveController):
    def __init__(self, settings):
        super().__init__(horizon=8)
        self.settings = settings
        self.integral_state = np.zeros(4, dtype=float)

    def reset(self):
        self.integral_state[:] = 0.0

    def compute_control(self, state, state_ref, torque_ref, dt):
        nominal = super().compute_control(state, state_ref, torque_ref, dt)
        tension_error = state[:4] - state_ref[:4]
        gains = np.array(self.settings["integral_gain_by_section"], dtype=float)
        leak = np.array(self.settings["leak_by_section"], dtype=float)
        limits = np.array(self.settings["integral_limit_by_section"], dtype=float)
        torque_limits = np.array(self.settings["torque_limit_by_section"], dtype=float)

        self.integral_state = leak * self.integral_state - gains * dt * tension_error
        self.integral_state = np.clip(self.integral_state, -limits, limits)
        total = nominal + self.integral_state
        return np.clip(total, -torque_limits, torque_limits)


settings = {
    "integral_gain_by_section": [3.5, 3.5, 2.8, 2.8],
    "leak_by_section": [0.996, 0.996, 0.988, 0.988],
    "integral_limit_by_section": [18.0, 18.0, 12.0, 12.0],
    "torque_limit_by_section": [138.0, 138.0, 138.0, 138.0],
}

result = {"controller_settings": settings, "cases": {}}
retrofit = RetrofittedController(settings)

for case_id in ("roll_change_step", "friction_bias_hold"):
    _, baseline_metrics = run_baseline_case(case_id)
    trace = run_case(case_id, retrofit)
    metrics = summarize_trace(trace)
    result["cases"][case_id] = {
        "baseline_tail_mean_abs_error": baseline_metrics["tail_mean_abs_error"],
        "tail_mean_abs_error": metrics["tail_mean_abs_error"],
        "tail_max_abs_error": metrics["tail_max_abs_error"],
        "peak_tension": metrics["peak_tension"],
        "peak_abs_torque": metrics["peak_abs_torque"],
        "trace": trace,
    }

output_path = Path("tension_retrofit_results.json")
with output_path.open("w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
PY
