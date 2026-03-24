#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from itertools import combinations

import numpy as np

INPUT_FILE = os.environ.get("INPUT_FILE", "/root/offshore_snapshot.json")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/wind_export_plan.json")
TOL = 1e-7


def load_instance():
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def clean_round(value):
    rounded = round(float(value), 2)
    if abs(rounded) < 0.005:
        return 0.0
    return rounded


def build_network(instance):
    buses = instance["buses"]
    cables = instance["cables"]
    base_mva = instance["base_mva"]
    bus_ids = [bus["id"] for bus in buses]
    bus_num_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    slack_idx = bus_num_to_idx[instance["reference_bus"]]
    non_slack = [idx for idx in range(len(buses)) if idx != slack_idx]

    B = np.zeros((len(buses), len(buses)), dtype=float)
    for cable in cables:
        f = bus_num_to_idx[cable["from"]]
        t = bus_num_to_idx[cable["to"]]
        b = 1.0 / cable["reactance_pu"]
        B[f, f] += b
        B[t, t] += b
        B[f, t] -= b
        B[t, f] -= b

    B_reduced_inv = np.linalg.inv(B[np.ix_(non_slack, non_slack)])
    return {
        "base_mva": base_mva,
        "bus_num_to_idx": bus_num_to_idx,
        "slack_idx": slack_idx,
        "non_slack": non_slack,
        "B_reduced_inv": B_reduced_inv,
    }


def theta_from_acceptance(instance, network, accepted):
    farms = instance["wind_farms"]
    injections = np.zeros(len(instance["buses"]), dtype=float)
    for value, farm in zip(accepted, farms):
        injections[network["bus_num_to_idx"][farm["bus"]]] += value / network["base_mva"]

    theta = np.zeros(len(instance["buses"]), dtype=float)
    theta[network["non_slack"]] = network["B_reduced_inv"] @ injections[network["non_slack"]]
    return theta


def flow_matrix(instance, network):
    n_farm = len(instance["wind_farms"])
    matrix = []
    for cable in instance["cables"]:
        row = []
        f = network["bus_num_to_idx"][cable["from"]]
        t = network["bus_num_to_idx"][cable["to"]]
        for farm_idx in range(n_farm):
            accepted = np.zeros(n_farm, dtype=float)
            accepted[farm_idx] = 1.0
            theta = theta_from_acceptance(instance, network, accepted)
            flow = (theta[f] - theta[t]) / cable["reactance_pu"] * network["base_mva"]
            row.append(flow)
        matrix.append(row)
    return np.array(matrix, dtype=float)


def build_constraints(instance, flow_coeffs):
    farms = instance["wind_farms"]
    n_farm = len(farms)
    A = []
    b = []

    for idx, farm in enumerate(farms):
        lower = np.zeros(n_farm, dtype=float)
        lower[idx] = -1.0
        A.append(lower)
        b.append(0.0)

        upper = np.zeros(n_farm, dtype=float)
        upper[idx] = 1.0
        A.append(upper)
        b.append(farm["available_mw"])

    for row, cable in zip(flow_coeffs, instance["cables"]):
        A.append(row)
        b.append(cable["limit_mw"])
        A.append(-row)
        b.append(cable["limit_mw"])

    return np.array(A, dtype=float), np.array(b, dtype=float)


def solve_vertex_lp(A, b, objective, equalities=None):
    n_var = A.shape[1]
    if equalities is None:
        C = np.zeros((0, n_var), dtype=float)
        d = np.zeros(0, dtype=float)
    else:
        C = np.array([row for row, _ in equalities], dtype=float)
        d = np.array([rhs for _, rhs in equalities], dtype=float)

    required_active = n_var - len(C)
    best_x = None
    best_obj = None

    for active in combinations(range(len(A)), required_active):
        system = np.vstack([C, A[list(active)]])
        rhs = np.concatenate([d, b[list(active)]])
        if np.linalg.matrix_rank(system) < n_var:
            continue

        candidate = np.linalg.solve(system, rhs)
        if np.max(A @ candidate - b) > TOL:
            continue
        if len(C) and np.max(np.abs(C @ candidate - d)) > TOL:
            continue

        value = float(objective @ candidate)
        if best_obj is None or value > best_obj + TOL:
            best_obj = value
            best_x = candidate

    if best_x is None:
        raise RuntimeError("no feasible solution found")

    return best_x, best_obj


def solve_instance(instance):
    network = build_network(instance)
    coeffs = flow_matrix(instance, network)
    A, b = build_constraints(instance, coeffs)

    stage1_solution, total_accepted = solve_vertex_lp(
        A=A,
        b=b,
        objective=np.ones(len(instance["wind_farms"]), dtype=float),
    )

    total_available = sum(farm["available_mw"] for farm in instance["wind_farms"])
    priority_base = int(total_available) + 1
    priority_weights = []
    max_priority = max(farm["curtailment_priority"] for farm in instance["wind_farms"])
    for farm in instance["wind_farms"]:
        exponent = max_priority - farm["curtailment_priority"]
        priority_weights.append(priority_base ** exponent)

    accepted, _ = solve_vertex_lp(
        A=A,
        b=b,
        objective=np.array(priority_weights, dtype=float),
        equalities=[(np.ones(len(instance["wind_farms"]), dtype=float), total_accepted)],
    )

    flows = coeffs @ accepted
    dispatch = []
    for value, farm in zip(accepted, instance["wind_farms"]):
        accepted_mw = clean_round(value)
        available_mw = clean_round(farm["available_mw"])
        dispatch.append(
            {
                "id": farm["id"],
                "bus": farm["bus"],
                "available_MW": available_mw,
                "accepted_MW": accepted_mw,
                "curtailed_MW": clean_round(available_mw - accepted_mw),
            }
        )

    cable_records = []
    for cable, flow in zip(instance["cables"], flows):
        loading_pct = abs(flow) / cable["limit_mw"] * 100.0
        cable_records.append(
            {
                "cable_id": cable["id"],
                "name": cable["name"],
                "from": cable["from"],
                "to": cable["to"],
                "flow_MW": clean_round(flow),
                "limit_MW": clean_round(cable["limit_mw"]),
                "loading_pct": clean_round(loading_pct),
                "_raw_loading_pct": float(loading_pct),
            }
        )

    most_congested = max(cable_records, key=lambda item: item["_raw_loading_pct"])
    most_congested.pop("_raw_loading_pct")

    total_accepted_mw = clean_round(np.sum(accepted))
    total_available_mw = clean_round(total_available)
    total_curtailed_mw = clean_round(total_available_mw - total_accepted_mw)

    plan = {
        "wind_farm_dispatch": dispatch,
        "summary": {
            "total_available_MW": total_available_mw,
            "total_accepted_MW": total_accepted_mw,
            "total_curtailed_MW": total_curtailed_mw,
            "delivered_to_shore_MW": total_accepted_mw,
            "curtailment_pct": clean_round(total_curtailed_mw / total_available_mw * 100.0),
        },
        "most_congested_cable": most_congested,
    }
    return plan


def main():
    instance = load_instance()
    plan = solve_instance(instance)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
PY
