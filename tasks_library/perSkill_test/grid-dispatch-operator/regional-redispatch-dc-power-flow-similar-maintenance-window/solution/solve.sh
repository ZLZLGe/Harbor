#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
from itertools import combinations

import numpy as np

INPUT_FILE = "/root/maintenance_window.json"
OUTPUT_FILE = "/root/redispatch_report.json"
TOL = 1e-7


with open(INPUT_FILE, encoding="utf-8") as f:
    data = json.load(f)

base_mva = data["base_mva"]
buses = data["buses"]
generators = data["generators"]
lines = data["lines"]
reference_bus = data["reference_bus"]

bus_ids = [bus["id"] for bus in buses]
bus_num_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
slack_idx = bus_num_to_idx[reference_bus]
n_bus = len(buses)
n_gen = len(generators)


def build_b_matrix():
    B = np.zeros((n_bus, n_bus), dtype=float)
    for line in lines:
        f = bus_num_to_idx[line["from"]]
        t = bus_num_to_idx[line["to"]]
        x = line["reactance_pu"]
        b = 1.0 / x
        B[f, f] += b
        B[t, t] += b
        B[f, t] -= b
        B[t, f] -= b
    return B


B = build_b_matrix()
non_slack = [idx for idx in range(n_bus) if idx != slack_idx]
B_reduced_inv = np.linalg.inv(B[np.ix_(non_slack, non_slack)])
total_load = sum(bus["demand_mw"] for bus in buses)


def theta_from_dispatch(dispatch_mw):
    injections = np.zeros(n_bus, dtype=float)

    for value, gen in zip(dispatch_mw, generators):
        injections[bus_num_to_idx[gen["bus"]]] += value / base_mva

    for bus in buses:
        injections[bus_num_to_idx[bus["id"]]] -= bus["demand_mw"] / base_mva

    if abs(float(np.sum(injections))) > 1e-6:
        raise ValueError("dispatch does not satisfy total power balance")

    theta = np.zeros(n_bus, dtype=float)
    theta[non_slack] = B_reduced_inv @ injections[non_slack]
    return theta


def line_flows_from_theta(theta):
    flows = []
    for line in lines:
        f = bus_num_to_idx[line["from"]]
        t = bus_num_to_idx[line["to"]]
        flow = (theta[f] - theta[t]) / line["reactance_pu"] * base_mva
        flows.append(flow)
    return np.array(flows, dtype=float)


def build_affine_line_model():
    zero_dispatch = np.zeros(n_gen, dtype=float)
    flow_constant = line_flows_from_theta(
        theta_from_unbalanced_dispatch(zero_dispatch)
    )
    flow_matrix = []
    for gen_idx in range(n_gen):
        unit_dispatch = np.zeros(n_gen, dtype=float)
        unit_dispatch[gen_idx] = 1.0
        unit_flow = line_flows_from_theta(theta_from_unbalanced_dispatch(unit_dispatch))
        flow_matrix.append(unit_flow - flow_constant)
    return flow_constant, np.column_stack(flow_matrix)


def theta_from_unbalanced_dispatch(dispatch_mw):
    injections = np.zeros(n_bus, dtype=float)

    for value, gen in zip(dispatch_mw, generators):
        injections[bus_num_to_idx[gen["bus"]]] += value / base_mva

    for bus in buses:
        injections[bus_num_to_idx[bus["id"]]] -= bus["demand_mw"] / base_mva

    theta = np.zeros(n_bus, dtype=float)
    theta[non_slack] = B_reduced_inv @ injections[non_slack]
    return theta


def enumerate_optimal_dispatch():
    flow_constant, flow_matrix = build_affine_line_model()

    inequalities = []
    for gen_idx, gen in enumerate(generators):
        selector = np.zeros(n_gen, dtype=float)
        selector[gen_idx] = 1.0
        inequalities.append((-selector, -gen["min_mw"], f'{gen["id"]}_min'))
        inequalities.append((selector, gen["max_mw"], f'{gen["id"]}_max'))

    for line_idx, line in enumerate(lines):
        coeffs = flow_matrix[line_idx]
        constant = flow_constant[line_idx]
        inequalities.append((coeffs, line["limit_mw"] - constant, f'{line["id"]}_upper'))
        inequalities.append((-coeffs, line["limit_mw"] + constant, f'{line["id"]}_lower'))

    balance_row = np.ones((1, n_gen), dtype=float)
    balance_rhs = np.array([total_load], dtype=float)

    best = None
    for active in combinations(range(len(inequalities)), n_gen - 1):
        matrix = np.vstack([balance_row] + [inequalities[idx][0] for idx in active])
        rhs = np.concatenate([balance_rhs, [inequalities[idx][1] for idx in active]])

        if np.linalg.matrix_rank(matrix) < n_gen:
            continue

        dispatch = np.linalg.solve(matrix, rhs)
        if any(coeffs @ dispatch - bound > 1e-6 for coeffs, bound, _ in inequalities):
            continue

        cost = float(sum(
            dispatch[idx] * generators[idx]["offer_usd_per_mwh"]
            for idx in range(n_gen)
        ))
        rounded_signature = tuple(round(float(value), 10) for value in dispatch)
        candidate = (cost, rounded_signature, dispatch)

        if best is None or candidate[:2] < best[:2]:
            best = candidate

    if best is None:
        raise RuntimeError("no feasible dispatch found")

    return best[2]


dispatch = enumerate_optimal_dispatch()
theta = theta_from_dispatch(dispatch)
flows = line_flows_from_theta(theta)
loadings = np.array(
    [abs(flow) / line["limit_mw"] * 100.0 for flow, line in zip(flows, lines)],
    dtype=float,
)

most_congested_idx = int(np.argmax(loadings))
most_congested_line = lines[most_congested_idx]
total_cost = float(sum(
    dispatch[idx] * generators[idx]["offer_usd_per_mwh"]
    for idx in range(n_gen)
))
total_adjustment = float(sum(
    abs(dispatch[idx] - generators[idx]["baseline_mw"])
    for idx in range(n_gen)
))

report = {
    "generator_dispatch": [
        {
            "id": gen["id"],
            "bus": gen["bus"],
            "baseline_MW": round(float(gen["baseline_mw"]), 4),
            "dispatch_MW": round(float(dispatch[idx]), 4),
            "delta_MW": round(float(dispatch[idx] - gen["baseline_mw"]), 4),
        }
        for idx, gen in enumerate(generators)
    ],
    "bus_angles_deg": [
        {
            "bus": bus["id"],
            "angle_deg": round(float(theta[bus_num_to_idx[bus["id"]]] * 180.0 / math.pi), 4),
        }
        for bus in buses
    ],
    "summary": {
        "total_generation_MW": round(float(np.sum(dispatch)), 4),
        "total_load_MW": round(float(total_load), 4),
        "total_cost_usd_per_hour": round(total_cost, 2),
        "total_adjustment_MW": round(total_adjustment, 4),
    },
    "most_congested_corridor": {
        "line_id": most_congested_line["id"],
        "name": most_congested_line["name"],
        "from": most_congested_line["from"],
        "to": most_congested_line["to"],
        "flow_MW": round(float(flows[most_congested_idx]), 4),
        "limit_MW": round(float(most_congested_line["limit_mw"]), 4),
        "loading_pct": round(float(loadings[most_congested_idx]), 2),
    },
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY
