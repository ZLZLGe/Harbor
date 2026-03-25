#!/bin/bash
set -e

cd /root

python3 <<'PY'
import csv
import json
import math


CASE_PATH = "/root/greenhouse_humidity_case.json"
TIMES_PATH = "/root/summary_minutes.csv"
OUTPUT_PATH = "/root/humidity_controller_plan.json"
HORIZON_MIN = 15.0


def round_float(value):
    return round(float(value), 6)


with open(CASE_PATH, "r", encoding="utf-8") as handle:
    case_data = json.load(handle)

with open(TIMES_PATH, "r", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    sample_times = [float(row["time_min"]) for row in reader]

K = case_data["process_model"]["K"]
tau_min = case_data["process_model"]["tau_min"]


def build_mode(mode_name, selector):
    mode_data = case_data["modes"][mode_name]
    lambda_candidates = mode_data["lambda_candidates_min"]
    lambda_min = selector(lambda_candidates)

    controller = {
        "Kp": round_float(tau_min / (K * lambda_min)),
        "Ki": round_float(1.0 / (K * lambda_min)),
        "Kd": 0.0,
    }

    initial = mode_data["initial_humidity_percent"]
    target = mode_data["target_humidity_percent"]
    samples = []

    for time_min in sample_times:
        predicted = target - (target - initial) * math.exp(-time_min / lambda_min)
        samples.append(
            {
                "time_min": round_float(time_min),
                "predicted_humidity_percent": round_float(predicted),
                "error_to_target_percent": round_float(target - predicted),
            }
        )

    end_humidity = samples[-1]["predicted_humidity_percent"]
    remaining_error = samples[-1]["error_to_target_percent"]
    progress_percent = (1.0 - math.exp(-HORIZON_MIN / lambda_min)) * 100.0

    return {
        "selected_lambda_min": round_float(lambda_min),
        "controller": controller,
        "response_summary": {
            "duration_min": round_float(HORIZON_MIN),
            "samples": samples,
            "end_humidity_percent": round_float(end_humidity),
            "remaining_error_percent": round_float(remaining_error),
            "progress_percent_at_horizon": round_float(progress_percent),
        },
    }


day_mode = build_mode("day", min)
night_mode = build_mode("night", max)

plan = {
    "case_id": case_data["case_id"],
    "selection_rule": "Day mode uses the smallest candidate lambda for a faster response; night mode uses the largest candidate lambda for a steadier response.",
    "process_model": {
        "K": round_float(K),
        "tau_min": round_float(tau_min),
    },
    "day_mode": day_mode,
    "night_mode": night_mode,
    "summary": "白天方案选更小的闭环时间常数以更快逼近目标湿度，夜间方案选更大的闭环时间常数以换取更平缓的变化。",
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(plan, handle, indent=2, ensure_ascii=False)
PY
