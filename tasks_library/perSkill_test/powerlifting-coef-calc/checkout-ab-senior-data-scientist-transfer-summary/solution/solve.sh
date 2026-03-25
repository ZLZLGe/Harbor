#!/bin/bash

set -euo pipefail

mkdir -p /root/results

python3 - <<'PY'
import csv
import json
import math

INPUT_FILE = "/root/data/checkout_funnel_events.csv"
OUTPUT_FILE = "/root/results/checkout_experiment_summary.json"

session_sets = {"control": set(), "treatment": set()}
purchase_sets = {"control": set(), "treatment": set()}

with open(INPUT_FILE, newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        variant = row["variant"]
        session_id = row["session_id"]
        session_sets[variant].add(session_id)
        if row["event_name"] == "purchase":
            purchase_sets[variant].add(session_id)

n_control = len(session_sets["control"])
n_treatment = len(session_sets["treatment"])
x_control = len(purchase_sets["control"])
x_treatment = len(purchase_sets["treatment"])

p_control = x_control / n_control
p_treatment = x_treatment / n_treatment
absolute_lift = p_treatment - p_control
relative_lift = absolute_lift / p_control

p_pool = (x_control + x_treatment) / (n_control + n_treatment)
se = math.sqrt(p_pool * (1.0 - p_pool) * ((1.0 / n_control) + (1.0 / n_treatment)))
z_score = absolute_lift / se
comparison_p_value = math.erfc(abs(z_score) / math.sqrt(2.0))

total_sessions = n_control + n_treatment
expected_per_group = total_sessions * 0.5
chi_square_stat = (
    ((n_control - expected_per_group) ** 2) / expected_per_group
    + ((n_treatment - expected_per_group) ** 2) / expected_per_group
)
srm_p_value = math.erfc(math.sqrt(chi_square_stat / 2.0))
srm_flagged = srm_p_value < 0.01

blocking_checks = []
if absolute_lift <= 0:
    blocking_checks.append("non_positive_lift")
if comparison_p_value >= 0.05:
    blocking_checks.append("not_significant")
if srm_flagged:
    blocking_checks.append("srm_flagged")

result = {
    "groups": {
        "control": {
            "sessions": n_control,
            "purchases": x_control,
            "conversion_rate": p_control,
        },
        "treatment": {
            "sessions": n_treatment,
            "purchases": x_treatment,
            "conversion_rate": p_treatment,
        },
    },
    "comparison": {
        "absolute_lift": absolute_lift,
        "relative_lift": relative_lift,
        "p_value": comparison_p_value,
    },
    "srm_check": {
        "expected_proportions": {
            "control": 0.5,
            "treatment": 0.5,
        },
        "observed_sessions": {
            "control": n_control,
            "treatment": n_treatment,
        },
        "chi_square_stat": chi_square_stat,
        "p_value": srm_p_value,
        "flagged": srm_flagged,
    },
    "decision": {
        "recommend_launch": len(blocking_checks) == 0,
        "blocking_checks": blocking_checks,
    },
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
