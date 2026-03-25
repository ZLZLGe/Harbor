#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
cd "$TASK_ROOT"
export PYTHONPATH="$TASK_ROOT:$TASK_ROOT/environment:${PYTHONPATH:-}"

python3 - <<'PY'
import json

from heater_controller_scaffold import evaluate_config


gain_candidates = [
    [0.45, 0.40],
    [0.55, 0.48],
    [0.65, 0.56],
    [0.75, 0.70],
    [0.90, 0.82],
]
leak_candidates = [
    [0.996, 0.995],
    [0.997, 0.996],
    [0.998, 0.997],
    [0.999, 0.998],
]
limit_candidates = [
    [1.2, 1.0],
    [1.5, 1.3],
    [1.8, 1.5],
    [2.2, 1.8],
]

best_config = None
best_score = None

for gains in gain_candidates:
    for leaks in leak_candidates:
        for limits in limit_candidates:
            config = {
                "integral_gain_by_zone": gains,
                "leak_by_zone": leaks,
                "integral_limit_by_zone": limits,
            }
            results = evaluate_config(config)
            tail_mean_worst = max(case["tail_mean_abs_error"] for case in results.values())
            tail_max_worst = max(case["tail_max_abs_error"] for case in results.values())
            improvement_worst = min(
                case["baseline_tail_mean_abs_error"] - case["tail_mean_abs_error"]
                for case in results.values()
            )
            feasible = (
                tail_mean_worst < 0.15
                and tail_max_worst < 0.23
                and improvement_worst >= 0.12
                and max(case["peak_temperature_c"] for case in results.values()) < 176.0
                and max(case["peak_heater_power_kw"] for case in results.values()) <= 9.0
            )
            if not feasible:
                continue
            score = (
                tail_mean_worst,
                tail_max_worst,
                -improvement_worst,
                sum(limits),
            )
            if best_score is None or score < best_score:
                best_score = score
                best_config = config

if best_config is None:
    raise SystemExit("no feasible integrator configuration found")

with open("heater_integrator_config.json", "w", encoding="utf-8") as handle:
    json.dump(best_config, handle, indent=2)
    handle.write("\n")
PY
