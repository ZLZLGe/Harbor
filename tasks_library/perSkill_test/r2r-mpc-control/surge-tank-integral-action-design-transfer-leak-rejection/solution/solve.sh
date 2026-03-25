#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/tank_controller_scaffold.py ]; then
    cd /root
else
    cd "$TASK_ROOT"
    export PYTHONPATH="$TASK_ROOT/environment${PYTHONPATH:+:$PYTHONPATH}"
fi

python3 <<'PY'
import math
from pathlib import Path

import yaml

from tank_controller_scaffold import evaluate_report


OUTPUT_PATH = Path("level_offset_report.yaml")


def qualifies(report):
    settings = report["controller_settings"]
    for case_payload in report["cases"].values():
        improvement = (
            case_payload["baseline_tail_mean_abs_level_error_m"]
            - case_payload["tail_mean_abs_level_error_m"]
        )
        if case_payload["tail_mean_abs_level_error_m"] >= 0.020:
            return False
        if case_payload["tail_max_abs_level_error_m"] >= 0.030:
            return False
        if improvement < 0.240:
            return False
        if case_payload["recovery_time_min"] is None or case_payload["recovery_time_min"] > 5.6:
            return False
        if case_payload["peak_overshoot_m"] >= 0.040:
            return False
        if case_payload["peak_valve_pct"] > settings["valve_max_pct"]:
            return False
        if len(case_payload["checkpoints"]) != 10:
            return False
    return True


candidate_gains = [20.0, 30.0, 40.0, 50.0, 60.0]
candidate_leaks = [0.99, 0.993, 0.995, 0.997]
candidate_limits = [12.0, 15.0, 18.0]
candidate_valve_caps = [80.0, 84.0, 88.0]

best_report = None
best_score = math.inf

for gain in candidate_gains:
    for leak in candidate_leaks:
        for limit in candidate_limits:
            for valve_cap in candidate_valve_caps:
                report = evaluate_report(
                    {
                        "controller_settings": {
                            "integral_gain_pct_per_m": gain,
                            "integral_leak": leak,
                            "integral_limit_pct": limit,
                            "valve_max_pct": valve_cap,
                        },
                        "cases": {},
                    }
                )
                if not qualifies(report):
                    continue

                score = 0.0
                for case_payload in report["cases"].values():
                    score += case_payload["tail_mean_abs_level_error_m"]
                    score += case_payload["tail_max_abs_level_error_m"]
                    score += case_payload["recovery_time_min"]
                    score += case_payload["peak_overshoot_m"] * 5.0

                if score < best_score:
                    best_score = score
                    best_report = report

if best_report is None:
    raise SystemExit("no controller setting satisfied the required report contract")

with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
    yaml.safe_dump(best_report, handle, sort_keys=False, allow_unicode=False)
PY
