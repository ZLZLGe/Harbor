#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np

INPUT_PATH = Path("/root/corridor_case.json")
OUTPUT_PATH = Path("/root/contingency_risk_rankings.json")
DELTA_THRESHOLD = 5.0


def round2(value):
    return round(float(value), 2)


def build_flow_solution(case, active_branches):
    buses = case["buses"]
    base_mva = float(case["baseMVA"])
    bus_index = {int(bus["id"]): idx for idx, bus in enumerate(buses)}
    slack_idx = next(idx for idx, bus in enumerate(buses) if bus["type"] == "slack")

    injections = np.array(
        [
            (float(bus["generation_MW"]) - float(bus["load_MW"])) / base_mva
            for bus in buses
        ],
        dtype=float,
    )

    n_bus = len(buses)
    bmat = np.zeros((n_bus, n_bus), dtype=float)
    for branch in active_branches:
        f = bus_index[int(branch["from"])]
        t = bus_index[int(branch["to"])]
        susceptance = 1.0 / float(branch["x_pu"])
        bmat[f, f] += susceptance
        bmat[t, t] += susceptance
        bmat[f, t] -= susceptance
        bmat[t, f] -= susceptance

    keep = [idx for idx in range(n_bus) if idx != slack_idx]
    theta = np.zeros(n_bus, dtype=float)
    theta[keep] = np.linalg.solve(bmat[np.ix_(keep, keep)], injections[keep])

    line_results = {}
    for branch in active_branches:
        f = bus_index[int(branch["from"])]
        t = bus_index[int(branch["to"])]
        flow_mw = base_mva * (theta[f] - theta[t]) / float(branch["x_pu"])
        loading_pct = abs(flow_mw) / float(branch["limit_MW"]) * 100.0
        line_results[branch["id"]] = {
            "id": branch["id"],
            "from": int(branch["from"]),
            "to": int(branch["to"]),
            "flow_MW": float(flow_mw),
            "limit_MW": float(branch["limit_MW"]),
            "loading_pct": float(loading_pct),
            "over_limit_pct": float(max(loading_pct - 100.0, 0.0)),
        }

    return line_results


def interface_rows(case, line_results, base_loading_map=None):
    rows = []
    for interface in case["interfaces"]:
        flow_mw = 0.0
        for element in interface["elements"]:
            branch = line_results.get(element["branch_id"])
            element_flow = 0.0 if branch is None else branch["flow_MW"]
            flow_mw += float(element["sign"]) * element_flow

        loading_pct = abs(flow_mw) / float(interface["limit_MW"]) * 100.0
        row = {
            "id": interface["id"],
            "flow_MW": float(flow_mw),
            "limit_MW": float(interface["limit_MW"]),
            "loading_pct": float(loading_pct),
        }
        if base_loading_map is not None:
            row["delta_loading_pct"] = float(loading_pct - base_loading_map[interface["id"]])
        rows.append(row)
    return rows


with INPUT_PATH.open(encoding="utf-8") as f:
    case = json.load(f)

base_lines = build_flow_solution(case, case["branches"])
base_interfaces = interface_rows(case, base_lines)
base_loading_map = {row["id"]: row["loading_pct"] for row in base_interfaces}

scenario_results = []
for contingency in case["contingencies"]:
    active_branches = [
        branch
        for branch in case["branches"]
        if branch["id"] != contingency["outaged_branch_id"]
    ]
    line_results = build_flow_solution(case, active_branches)
    most_loaded = min(
        (
            (
                -row["loading_pct"],
                row["id"],
                row,
            )
            for row in line_results.values()
        )
    )[2]

    affected_interfaces = []
    for row in interface_rows(case, line_results, base_loading_map):
        if abs(row["delta_loading_pct"]) + 1e-9 < DELTA_THRESHOLD:
            continue
        affected_interfaces.append(
            {
                "id": row["id"],
                "flow_MW": round2(row["flow_MW"]),
                "limit_MW": round2(row["limit_MW"]),
                "loading_pct": round2(row["loading_pct"]),
                "delta_loading_pct": round2(row["delta_loading_pct"]),
            }
        )

    affected_interfaces.sort(
        key=lambda item: (-abs(item["delta_loading_pct"]), item["id"])
    )

    scenario_results.append(
        {
            "scenario_id": contingency["id"],
            "outaged_branch_id": contingency["outaged_branch_id"],
            "most_loaded_line": {
                "id": most_loaded["id"],
                "from": most_loaded["from"],
                "to": most_loaded["to"],
                "flow_MW": round2(most_loaded["flow_MW"]),
                "limit_MW": round2(most_loaded["limit_MW"]),
                "loading_pct": round2(most_loaded["loading_pct"]),
                "over_limit_pct": round2(most_loaded["over_limit_pct"]),
            },
            "max_over_limit_pct": round2(most_loaded["over_limit_pct"]),
            "affected_interfaces": affected_interfaces,
        }
    )

top_3 = sorted(
    scenario_results,
    key=lambda item: (-item["max_over_limit_pct"], item["scenario_id"]),
)[:3]

output = {
    "case_id": case["case_id"],
    "scenario_results": scenario_results,
    "top_3_riskiest_scenarios": [
        {
            "scenario_id": row["scenario_id"],
            "outaged_branch_id": row["outaged_branch_id"],
            "max_over_limit_pct": row["max_over_limit_pct"],
            "most_loaded_line_id": row["most_loaded_line"]["id"],
        }
        for row in top_3
    ],
}

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
PY
