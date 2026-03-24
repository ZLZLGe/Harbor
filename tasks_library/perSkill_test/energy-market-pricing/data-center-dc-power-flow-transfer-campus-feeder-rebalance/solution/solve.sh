#!/bin/bash
set -e

pip3 install --break-system-packages numpy==1.26.4 -q

python3 <<'PY'
import json
import math
from pathlib import Path

import numpy as np


def rounded(value):
    return round(float(value), 4)


network = json.loads(Path("/root/campus_network.json").read_text())
plan = json.loads(Path("/root/rebalance_plan.json").read_text())

base_mva = float(network["baseMVA"])
buses = network["buses"]
feeders = network["feeders"]
hall_bus_ids = [int(bus) for bus in network["hall_bus_ids"]]
tie_feeder_ids = list(network["tie_feeder_ids"])
slack_bus = int(network["slack_bus"])
loading_alert_pct = float(plan["loading_alert_pct"])

bus_order = [int(bus["bus"]) for bus in buses]
bus_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_order)}
slack_idx = bus_to_idx[slack_bus]


def injection_vector(entries):
    entry_map = {int(item["bus"]): float(item["net_injection_MW"]) for item in entries}
    return np.array([entry_map[bus_id] for bus_id in bus_order], dtype=float)


def solve_case(entries):
    injections_mw = injection_vector(entries)
    n_bus = len(bus_order)
    b_matrix = np.zeros((n_bus, n_bus), dtype=float)

    for feeder in feeders:
        from_idx = bus_to_idx[int(feeder["from_bus"])]
        to_idx = bus_to_idx[int(feeder["to_bus"])]
        susceptance = 1.0 / float(feeder["x_pu"])

        b_matrix[from_idx, from_idx] += susceptance
        b_matrix[to_idx, to_idx] += susceptance
        b_matrix[from_idx, to_idx] -= susceptance
        b_matrix[to_idx, from_idx] -= susceptance

    keep = [idx for idx in range(n_bus) if idx != slack_idx]
    theta = np.zeros(n_bus, dtype=float)
    theta[keep] = np.linalg.solve(
        b_matrix[np.ix_(keep, keep)],
        injections_mw[keep] / base_mva,
    )

    feeder_flows = []
    feeder_by_id = {}
    for feeder in feeders:
        from_bus = int(feeder["from_bus"])
        to_bus = int(feeder["to_bus"])
        from_idx = bus_to_idx[from_bus]
        to_idx = bus_to_idx[to_bus]
        flow_mw = (theta[from_idx] - theta[to_idx]) / float(feeder["x_pu"]) * base_mva
        rating_mw = float(feeder["rating_MW"])

        entry = {
            "feeder_id": feeder["feeder_id"],
            "from_bus": from_bus,
            "to_bus": to_bus,
            "feeder_class": feeder["feeder_class"],
            "flow_MW": rounded(flow_mw),
            "rating_MW": rounded(rating_mw),
            "loading_pct": rounded(abs(flow_mw) / rating_mw * 100.0),
        }
        feeder_flows.append(entry)
        feeder_by_id[feeder["feeder_id"]] = entry

    overloaded_ties = [
        feeder_by_id[feeder_id]
        for feeder_id in tie_feeder_ids
        if feeder_by_id[feeder_id]["loading_pct"] >= loading_alert_pct
    ]

    return {
        "theta": theta,
        "feeder_flows": feeder_flows,
        "feeder_by_id": feeder_by_id,
        "overloaded_ties": overloaded_ties,
    }


baseline = solve_case(plan["baseline_bus_injections_MW"])
rebalanced = solve_case(plan["rebalanced_bus_injections_MW"])

hall_bus_angle_changes = []
for bus_id in hall_bus_ids:
    baseline_angle_deg = rounded(baseline["theta"][bus_to_idx[bus_id]] * 180.0 / math.pi)
    rebalanced_angle_deg = rounded(rebalanced["theta"][bus_to_idx[bus_id]] * 180.0 / math.pi)
    hall_bus_angle_changes.append(
        {
            "bus": bus_id,
            "baseline_angle_deg": baseline_angle_deg,
            "rebalanced_angle_deg": rebalanced_angle_deg,
            "absolute_change_deg": rounded(abs(rebalanced_angle_deg - baseline_angle_deg)),
        }
    )

hall_bus_angle_changes.sort(key=lambda item: (-item["absolute_change_deg"], item["bus"]))

feeders_with_relief = []
for feeder in feeders:
    feeder_id = feeder["feeder_id"]
    baseline_abs_flow = abs(baseline["feeder_by_id"][feeder_id]["flow_MW"])
    rebalanced_abs_flow = abs(rebalanced["feeder_by_id"][feeder_id]["flow_MW"])
    relief_mw = rounded(max(0.0, baseline_abs_flow - rebalanced_abs_flow))

    if relief_mw <= 0:
        continue

    feeders_with_relief.append(
        {
            "feeder_id": feeder_id,
            "from_bus": int(feeder["from_bus"]),
            "to_bus": int(feeder["to_bus"]),
            "baseline_abs_flow_MW": rounded(baseline_abs_flow),
            "rebalanced_abs_flow_MW": rounded(rebalanced_abs_flow),
            "relief_MW": relief_mw,
        }
    )

feeders_with_relief.sort(key=lambda item: (-item["relief_MW"], item["feeder_id"]))

baseline_tie_ids = {entry["feeder_id"] for entry in baseline["overloaded_ties"]}
rebalanced_tie_ids = {entry["feeder_id"] for entry in rebalanced["overloaded_ties"]}

report = {
    "scenario": {
        "name": plan["scenario_name"],
        "slack_bus": slack_bus,
        "baseline_layout": plan["baseline_layout_name"],
        "rebalanced_layout": plan["rebalanced_layout_name"],
        "tie_feeder_ids": tie_feeder_ids,
    },
    "baseline_layout": {
        "feeder_flows": baseline["feeder_flows"],
        "overloaded_ties": baseline["overloaded_ties"],
    },
    "rebalanced_layout": {
        "feeder_flows": rebalanced["feeder_flows"],
        "overloaded_ties": rebalanced["overloaded_ties"],
    },
    "comparison": {
        "hall_bus_angle_changes_deg": hall_bus_angle_changes[: int(plan["top_angle_change_count"])],
        "feeders_with_most_relief": feeders_with_relief[: int(plan["top_relief_count"])],
        "tie_overload_reduction_count": len(baseline["overloaded_ties"]) - len(rebalanced["overloaded_ties"]),
        "ties_relieved": sorted(baseline_tie_ids - rebalanced_tie_ids),
    },
}

Path("/root/campus_rebalance_summary.json").write_text(json.dumps(report, indent=2) + "\n")
PY
