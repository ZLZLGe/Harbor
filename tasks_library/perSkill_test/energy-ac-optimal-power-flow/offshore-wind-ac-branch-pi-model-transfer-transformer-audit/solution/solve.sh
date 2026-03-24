#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
import os
from pathlib import Path


FIELDS = (
    "p_from_MW",
    "q_from_MVAr",
    "s_from_MVA",
    "p_to_MW",
    "q_to_MVAr",
    "s_to_MVA",
)
MODEL_ORDER = (
    "as_modeled",
    "sign_convention_error",
    "tap_ratio_not_applied",
    "phase_shift_sign_error",
)
ISSUE_BY_MODEL = {
    "as_modeled": "none",
    "sign_convention_error": "sign_convention_error",
    "tap_ratio_not_applied": "tap_ratio_not_applied",
    "phase_shift_sign_error": "phase_shift_sign_error",
}


def resolve_input() -> Path:
    root_path = Path("/root/offshore_transformer_case.json")
    try:
        exists = root_path.exists()
    except PermissionError:
        exists = False
    if exists:
        return root_path
    return Path("environment/offshore_transformer_case.json")


def resolve_output() -> Path:
    root_dir = Path("/root")
    if root_dir.exists() and os.access(root_dir, os.W_OK):
        return root_dir / "transformer_diagnostics.json"
    return Path("transformer_diagnostics.json")


def rounded(value: float) -> float:
    return round(float(value), 6)


def compute_flow(branch: dict, voltage_by_bus: dict[int, tuple[float, float]], base_mva: float, model: str) -> dict:
    vm_i, va_i_deg = voltage_by_bus[int(branch["from_bus"])]
    vm_j, va_j_deg = voltage_by_bus[int(branch["to_bus"])]
    tap = float(branch["tap"])
    shift_deg = float(branch["shift_deg"])

    if model == "tap_ratio_not_applied":
        tap = 1.0
    if model == "phase_shift_sign_error":
        shift_deg = -shift_deg

    r = float(branch["r_pu"])
    x = float(branch["x_pu"])
    bc = float(branch["b_pu"])
    denom = r * r + x * x
    g = r / denom
    b = -x / denom

    va_i = math.radians(va_i_deg)
    va_j = math.radians(va_j_deg)
    shift = math.radians(shift_deg)
    inv_t = 1.0 / tap
    inv_t2 = inv_t * inv_t

    delta_ij = va_i - va_j - shift
    p_from = g * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ij) + b * math.sin(delta_ij)
    )
    q_from = -(b + bc / 2.0) * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ij) - b * math.cos(delta_ij)
    )

    delta_ji = va_j - va_i + shift
    p_to = g * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ji) + b * math.sin(delta_ji)
    )
    q_to = -(b + bc / 2.0) * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ji) - b * math.cos(delta_ji)
    )

    p_from *= base_mva
    q_from *= base_mva
    p_to *= base_mva
    q_to *= base_mva

    if model == "sign_convention_error":
        p_from = -p_from
        q_from = -q_from
        p_to = -p_to
        q_to = -q_to

    s_from = math.hypot(p_from, q_from)
    s_to = math.hypot(p_to, q_to)

    return {
        "p_from_MW": p_from,
        "q_from_MVAr": q_from,
        "s_from_MVA": s_from,
        "p_to_MW": p_to,
        "q_to_MVAr": q_to,
        "s_to_MVA": s_to,
    }


def rmse(left: dict, right: dict) -> float:
    return math.sqrt(sum((float(left[field]) - float(right[field])) ** 2 for field in FIELDS) / len(FIELDS))


def main() -> None:
    case = json.loads(resolve_input().read_text())
    base_mva = float(case["baseMVA"])
    voltage_by_bus = {
        int(bus["id"]): (float(bus["vm_pu"]), float(bus["va_deg"]))
        for bus in case["buses"]
    }
    expected_by_id = {
        item["id"]: {field: float(item[field]) for field in FIELDS}
        for item in case["meter_expectations"]
    }

    diagnostics = []
    for branch in case["transformers"]:
        actual_raw = compute_flow(branch, voltage_by_bus, base_mva, "as_modeled")
        expected_raw = expected_by_id[branch["id"]]
        candidate_raw = {
            model: rmse(compute_flow(branch, voltage_by_bus, base_mva, model), expected_raw)
            for model in MODEL_ORDER
        }
        best_model = min(MODEL_ORDER, key=lambda model: (candidate_raw[model], model))

        delta_raw = {
            field: expected_raw[field] - actual_raw[field]
            for field in FIELDS
        }

        diagnostics.append(
            {
                "id": branch["id"],
                "from_bus": int(branch["from_bus"]),
                "to_bus": int(branch["to_bus"]),
                "status": "consistent" if best_model == "as_modeled" else "suspect",
                "suspected_issue": ISSUE_BY_MODEL[best_model],
                "best_matching_model": best_model,
                "as_modeled_rmse": rounded(candidate_raw["as_modeled"]),
                "max_abs_p_error_MW": rounded(max(abs(delta_raw["p_from_MW"]), abs(delta_raw["p_to_MW"]))),
                "max_abs_q_error_MVAr": rounded(max(abs(delta_raw["q_from_MVAr"]), abs(delta_raw["q_to_MVAr"]))),
                "max_abs_s_error_MVA": rounded(max(abs(delta_raw["s_from_MVA"]), abs(delta_raw["s_to_MVA"]))),
                "actual": {field: rounded(value) for field, value in actual_raw.items()},
                "expected": {field: rounded(value) for field, value in expected_raw.items()},
                "delta_expected_minus_actual": {field: rounded(value) for field, value in delta_raw.items()},
                "candidate_rmse": {model: rounded(value) for model, value in candidate_raw.items()},
            }
        )

    diagnostics.sort(
        key=lambda item: (-item["as_modeled_rmse"], -item["max_abs_s_error_MVA"], item["id"])
    )
    for index, item in enumerate(diagnostics, start=1):
        item["diagnostic_rank"] = index

    summary = {
        "transformer_count": len(diagnostics),
        "consistent_meter_count": sum(1 for item in diagnostics if item["status"] == "consistent"),
        "suspect_meter_count": sum(1 for item in diagnostics if item["status"] == "suspect"),
        "largest_as_modeled_rmse": diagnostics[0]["as_modeled_rmse"],
        "largest_error_transformer_id": diagnostics[0]["id"],
        "worst_absolute_p_error_MW": rounded(max(item["max_abs_p_error_MW"] for item in diagnostics)),
        "worst_absolute_q_error_MVAr": rounded(max(item["max_abs_q_error_MVAr"] for item in diagnostics)),
        "worst_absolute_s_error_MVA": rounded(max(item["max_abs_s_error_MVA"] for item in diagnostics)),
    }
    issue_counts = {
        "none": sum(1 for item in diagnostics if item["suspected_issue"] == "none"),
        "sign_convention_error": sum(
            1 for item in diagnostics if item["suspected_issue"] == "sign_convention_error"
        ),
        "tap_ratio_not_applied": sum(
            1 for item in diagnostics if item["suspected_issue"] == "tap_ratio_not_applied"
        ),
        "phase_shift_sign_error": sum(
            1 for item in diagnostics if item["suspected_issue"] == "phase_shift_sign_error"
        ),
    }

    output = {
        "case_id": case["case_id"],
        "summary": summary,
        "diagnostics": diagnostics,
        "issue_counts": issue_counts,
    }
    resolve_output().write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
PY
