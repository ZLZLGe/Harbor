#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
import os
from pathlib import Path


def resolve_input() -> Path:
    primary = Path("/root/contingency_cases.json")
    try:
        exists = primary.exists()
    except PermissionError:
        exists = False
    if exists:
        return primary
    return Path("environment/contingency_cases.json")


def resolve_output() -> Path:
    primary = Path("/root/contingency_screen.json")
    if os.access(primary.parent, os.W_OK):
        return primary
    return Path("contingency_screen.json")


def branch_flow(branch: dict, voltage_by_bus: dict, base_mva: float) -> dict:
    vm_i, va_i_deg = voltage_by_bus[int(branch["from_bus"])]
    vm_j, va_j_deg = voltage_by_bus[int(branch["to_bus"])]
    tap = float(branch["tap"]) if abs(float(branch["tap"])) >= 1e-12 else 1.0
    shift = math.radians(float(branch["shift_deg"]))
    r = float(branch["r_pu"])
    x = float(branch["x_pu"])
    bc = float(branch["b_pu"])

    if abs(r) < 1e-12 and abs(x) < 1e-12:
        g = 0.0
        b = 0.0
    else:
        denom = r * r + x * x
        g = r / denom
        b = -x / denom

    va_i = math.radians(va_i_deg)
    va_j = math.radians(va_j_deg)
    inv_t = 1.0 / tap
    inv_t2 = inv_t * inv_t

    delta_ij = va_i - va_j - shift
    p_from_pu = g * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ij) + b * math.sin(delta_ij)
    )
    q_from_pu = -(b + bc / 2.0) * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ij) - b * math.cos(delta_ij)
    )

    delta_ji = va_j - va_i + shift
    p_to_pu = g * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ji) + b * math.sin(delta_ji)
    )
    q_to_pu = -(b + bc / 2.0) * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ji) - b * math.cos(delta_ji)
    )

    p_from = p_from_pu * base_mva
    q_from = q_from_pu * base_mva
    p_to = p_to_pu * base_mva
    q_to = q_to_pu * base_mva
    s_from = math.hypot(p_from, q_from)
    s_to = math.hypot(p_to, q_to)
    worst = max(s_from, s_to)
    limit = float(branch["rateA_MVA"])
    overload = max(0.0, worst - limit)

    return {
        "id": branch["id"],
        "from_bus": int(branch["from_bus"]),
        "to_bus": int(branch["to_bus"]),
        "p_from_MW": p_from,
        "q_from_MVAr": q_from,
        "s_from_MVA": s_from,
        "p_to_MW": p_to,
        "q_to_MVAr": q_to,
        "s_to_MVA": s_to,
        "limit_MVA": limit,
        "loading_pct": 0.0 if limit <= 0.0 else 100.0 * worst / limit,
        "overload_MVA": overload,
    }


def choose_worst_branch(records: list[dict]) -> dict:
    return sorted(records, key=lambda item: (-item["overload_MVA"], -item["loading_pct"], item["id"]))[0]


def main() -> None:
    cases = json.loads(resolve_input().read_text())
    base_mva = float(cases["baseMVA"])

    scenario_results = []
    for scenario in cases["scenarios"]:
        voltage_by_bus = {
            int(item["bus"]): (float(item["vm_pu"]), float(item["va_deg"]))
            for item in scenario["bus_voltages"]
        }
        surviving = [
            branch_flow(branch, voltage_by_bus, base_mva)
            for branch in cases["branches"]
            if branch["id"] != scenario["outaged_branch_id"]
        ]
        worst_branch = choose_worst_branch(surviving)
        scenario_results.append(
            {
                "scenario_id": scenario["scenario_id"],
                "outaged_branch_id": scenario["outaged_branch_id"],
                "surviving_branch_count": len(surviving),
                "overloaded_branch_count": sum(1 for item in surviving if item["overload_MVA"] > 0.0),
                "max_loading_pct": worst_branch["loading_pct"],
                "max_overload_MVA": worst_branch["overload_MVA"],
                "worst_branch": worst_branch,
            }
        )

    scenario_results.sort(
        key=lambda item: (-item["max_overload_MVA"], -item["max_loading_pct"], item["scenario_id"])
    )
    for index, item in enumerate(scenario_results, start=1):
        item["severity_rank"] = index

    worst_scenario = scenario_results[0]
    report = {
        "study_id": cases["study_id"],
        "summary": {
            "scenario_count": len(scenario_results),
            "scenarios_with_overloads": sum(1 for item in scenario_results if item["overloaded_branch_count"] > 0),
            "most_dangerous_scenario_id": worst_scenario["scenario_id"],
            "most_dangerous_outaged_branch_id": worst_scenario["outaged_branch_id"],
            "overall_worst_branch_id": worst_scenario["worst_branch"]["id"],
            "overall_worst_loading_pct": worst_scenario["max_loading_pct"],
            "overall_worst_overload_MVA": worst_scenario["max_overload_MVA"],
        },
        "scenario_results": scenario_results,
    }

    resolve_output().write_text(json.dumps(report, indent=2) + "\n")


main()
PY
