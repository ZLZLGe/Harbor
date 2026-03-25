#!/bin/bash

set -euo pipefail

INPUT_DIR="${METHOD_MATRIX_INPUT_DIR:-/root/planning_inputs}"
OUTPUT_FILE="${METHOD_MATRIX_OUTPUT_FILE:-/root/method_matrix.json}"

python3 - <<'PY'
import csv
import json
import os
from pathlib import Path


input_dir = Path(os.environ.get("METHOD_MATRIX_INPUT_DIR", "/root/planning_inputs"))
output_file = Path(os.environ.get("METHOD_MATRIX_OUTPUT_FILE", "/root/method_matrix.json"))


def choose_method(row):
    template_count = int(row["template_count"])
    repeatability = row["source_repeatability"]
    latency = row["latency_budget"]
    compute_budget = row["compute_budget"]
    review_requirement = row["review_requirement"]
    false_positive_tolerance = row["false_positive_tolerance"]
    station_mix = row["station_mix"]
    goal = row["primary_goal"]
    data_availability = row["data_availability"]
    context = row["context"]

    if review_requirement == "full human review" or false_positive_tolerance == "very_low":
        reason = (
            f"Manual review fits {context.lower()} because the project requires a defensible audited catalog, "
            f"has {row['analyst_capacity']} available, and prioritizes almost no false positives over speed."
        )
        return "manual", reason

    if template_count >= 100 and repeatability == "high":
        reason = (
            f"Template matching is best because the scenario already has {template_count} vetted templates and "
            f"the goal is to detect the smallest recurring events in a known cluster during offline batch work."
        )
        return "template_matching", reason

    if latency == "seconds" and compute_budget == "low":
        reason = (
            f"STA/LTA matches the seconds-level latency target and low compute budget, and the {station_mix.lower()} "
            f"network only needs a fast first-stage trigger for larger felt shaking."
        )
        return "sta_lta", reason

    reason = (
        f"Deep learning is the best fit for this temporary deployment because it has continuous data from {station_mix.lower()}, "
        f"needs a more complete local aftershock catalog, and does not yet have reusable templates."
    )
    return "deep_learning", reason


with (input_dir / "deployment_matrix.csv").open("r", encoding="utf-8", newline="") as fh:
    rows = list(csv.DictReader(fh))

recommendations = []
for row in sorted(rows, key=lambda item: item["scenario_id"]):
    method, reason = choose_method(row)
    recommendations.append(
        {
            "scenario_id": row["scenario_id"],
            "recommended_method": method,
            "reason": reason,
        }
    )

payload = {
    "matrix_version": "1.0",
    "recommendations": recommendations,
}

output_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
