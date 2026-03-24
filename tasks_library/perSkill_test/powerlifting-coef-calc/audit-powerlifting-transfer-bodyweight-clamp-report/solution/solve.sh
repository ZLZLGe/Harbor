#!/bin/bash

set -euo pipefail

INPUT_FILE="/root/data/extreme_bodyweight_audit_input.json"
OUTPUT_FILE="/root/data/bodyweight_clamp_audit.json"

python3 - <<'PY'
import json
from pathlib import Path

INPUT_FILE = Path("/root/data/extreme_bodyweight_audit_input.json")
OUTPUT_FILE = Path("/root/data/bodyweight_clamp_audit.json")

MALE_COEFFICIENTS = (-0.0000010930, 0.0007391293, -0.1918759221, 24.0900756, -307.75076)
FEMALE_COEFFICIENTS = (-0.0000010706, 0.0005158568, -0.1126655495, 13.6175032, -57.96288)


def clamp_bodyweight(sex: str, bodyweight: float) -> float:
    if sex == "M":
        return max(40.0, min(210.0, bodyweight))
    return max(40.0, min(150.0, bodyweight))


def calculate_dots(sex: str, bodyweight: float, total: float) -> float:
    adjusted = clamp_bodyweight(sex, bodyweight)
    if sex == "M":
        a, b, c, d, e = MALE_COEFFICIENTS
    else:
        a, b, c, d, e = FEMALE_COEFFICIENTS

    denominator = a * adjusted**4 + b * adjusted**3 + c * adjusted**2 + d * adjusted + e
    return round(total * (500.0 / denominator), 3)


def adjustment_label(original: float, adjusted: float) -> str:
    if adjusted > original:
        return "floor_to_min"
    if adjusted < original:
        return "cap_to_max"
    return "none"


payload = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
entries = []
summary = {
    "athlete_count": 0,
    "adjusted_count": 0,
    "floor_adjustment_count": 0,
    "cap_adjustment_count": 0,
    "unchanged_count": 0,
}

for athlete in payload["athletes"]:
    sex = athlete["profile"]["sex"]
    original_bodyweight = float(athlete["weigh_in"]["bodyweight_kg"])
    lifts = athlete["best_lifts_kg"]
    total = round(float(lifts["squat"]) + float(lifts["bench"]) + float(lifts["deadlift"]), 3)
    applied_bodyweight = clamp_bodyweight(sex, original_bodyweight)
    adjustment = adjustment_label(original_bodyweight, applied_bodyweight)
    dots = calculate_dots(sex, original_bodyweight, total)

    summary["athlete_count"] += 1
    if adjustment == "none":
        summary["unchanged_count"] += 1
    else:
        summary["adjusted_count"] += 1
        if adjustment == "floor_to_min":
            summary["floor_adjustment_count"] += 1
        else:
            summary["cap_adjustment_count"] += 1

    entries.append(
        {
            "athlete_id": athlete["athlete_id"],
            "lifter_name": athlete["profile"]["lifter_name"],
            "sex": sex,
            "original_bodyweight_kg": original_bodyweight,
            "applied_bodyweight_kg": applied_bodyweight,
            "adjustment": adjustment,
            "total_kg": total,
            "dots": dots,
        }
    )

report = {
    "meet_id": payload["meet_id"],
    "audit_batch": payload["audit_batch"],
    "summary": summary,
    "entries": entries,
}

OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
