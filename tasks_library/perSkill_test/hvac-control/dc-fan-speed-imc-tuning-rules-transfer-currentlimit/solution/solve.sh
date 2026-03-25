#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
export TASK_ROOT

cd "$TASK_ROOT"

python3 <<'PY'
import csv
import json
import math
import os
import tomllib


TASK_ROOT = os.environ["TASK_ROOT"]
CASE_PATH = os.path.join(TASK_ROOT, "motor_speed_case.toml")
CHECKPOINTS_PATH = os.path.join(TASK_ROOT, "checkpoints_ms.tsv")
OUTPUT_PATH = os.path.join(TASK_ROOT, "motor_speed_tuning_card.json")


def round_float(value):
    return round(float(value), 6)


with open(CASE_PATH, "rb") as handle:
    case_data = tomllib.load(handle)

with open(CHECKPOINTS_PATH, "r", encoding="utf-8") as handle:
    checkpoints_ms = [float(row["time_ms"]) for row in csv.DictReader(handle, delimiter="\t")]

process = case_data["process_model"]
operating = case_data["operating_point"]
K = process["K_rpm_per_amp"]
tau = process["tau_sec"]
initial = operating["initial_speed_rpm"]
target = operating["target_speed_rpm"]
current_limit = operating["current_limit_a"]
horizon = case_data["response_horizon_sec"]


def controller(lambda_sec):
    return {
        "Kp": round_float(tau / (K * lambda_sec)),
        "Ki": round_float(1.0 / (K * lambda_sec)),
        "Kd": 0.0,
    }


def predicted_speed(lambda_sec, time_sec):
    return target - (target - initial) * math.exp(-time_sec / lambda_sec)


def predicted_current(lambda_sec, time_sec):
    factor = math.exp(-time_sec / lambda_sec)
    numerator = target + (target - initial) * (tau / lambda_sec - 1.0) * factor
    return numerator / K


def peak_current(lambda_sec):
    steady_state_current = target / K
    startup_current = (initial + (target - initial) * tau / lambda_sec) / K
    return max(steady_state_current, startup_current)


candidate_review = []
feasible = []

for lambda_sec in case_data["candidate_lambda_sec"]:
    current_peak = peak_current(lambda_sec)
    item = {
        "lambda_sec": round_float(lambda_sec),
        "controller": controller(lambda_sec),
        "steady_state_current_a": round_float(target / K),
        "peak_current_a": round_float(current_peak),
        "within_current_limit": current_peak <= current_limit + 1e-12,
    }
    candidate_review.append(item)
    if item["within_current_limit"]:
        feasible.append(item)

selected = min(feasible, key=lambda item: item["lambda_sec"])
selected_lambda = selected["lambda_sec"]
selected_peak = selected["peak_current_a"]
final_speed = predicted_speed(selected_lambda, horizon)
final_error = target - final_speed

checkpoints = []
for time_ms in checkpoints_ms:
    time_sec = time_ms / 1000.0
    speed = predicted_speed(selected_lambda, time_sec)
    current = predicted_current(selected_lambda, time_sec)
    checkpoints.append(
        {
            "time_ms": round_float(time_ms),
            "predicted_speed_rpm": round_float(speed),
            "predicted_current_a": round_float(current),
            "tracking_error_rpm": round_float(target - speed),
        }
    )

output = {
    "case_id": case_data["case_id"],
    "selection_rule": "Evaluate every candidate lambda, keep only peak-current-safe options, then choose the smallest feasible lambda.",
    "process_model": {
        "K_rpm_per_amp": round_float(K),
        "tau_sec": round_float(tau),
    },
    "operating_point": {
        "initial_speed_rpm": round_float(initial),
        "target_speed_rpm": round_float(target),
        "current_limit_a": round_float(current_limit),
    },
    "selected_lambda_sec": round_float(selected_lambda),
    "controller": selected["controller"],
    "candidate_review": candidate_review,
    "tracking_summary": {
        "response_horizon_sec": round_float(horizon),
        "steady_state_current_a": round_float(target / K),
        "peak_current_a": round_float(selected_peak),
        "current_margin_a": round_float(current_limit - selected_peak),
        "final_speed_rpm": round_float(final_speed),
        "final_error_rpm": round_float(final_error),
        "steady_state_error_rpm": 0.0,
        "checkpoints": checkpoints,
    },
    "summary": "The selected lambda is the smallest candidate whose predicted peak current stays within the drive limit while still giving the fastest permitted speed response.",
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(output, handle, indent=2)
    handle.write("\n")
PY
