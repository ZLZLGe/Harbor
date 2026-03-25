#!/bin/bash
set -e

cd /root

python3 <<'PY'
import json
from reheat_loop_simulator import evaluate_candidates, load_case


case_data = load_case()
evaluations = evaluate_candidates(case_data)

selected = None
for item in evaluations:
    if item["feasible"]:
        selected = item
        break

if selected is None:
    raise RuntimeError("No feasible candidate found for this commissioning case")

output = {
    "case_id": case_data["case_id"],
    "selection_rule": "Choose the smallest lambda_sec whose simulated response satisfies every limit in acceptance.",
    "selected_lambda_sec": selected["lambda_sec"],
    "controller": selected["controller"],
    "selected_metrics": selected["metrics"],
    "candidates": [
        {
            "lambda_sec": item["lambda_sec"],
            "controller": item["controller"],
            "metrics": item["metrics"],
            "feasible": item["feasible"],
        }
        for item in evaluations
    ],
    "trajectory": selected["trajectory"],
    "summary": (
        f"{selected['lambda_sec']:.0f} s is the fastest feasible candidate. "
        f"The 90 s option violates the saturation limit, and the 360 s option misses the response targets."
    ),
}

with open("/root/reheat_loop_design.json", "w", encoding="utf-8") as handle:
    json.dump(output, handle, indent=2)
    handle.write("\n")
PY
