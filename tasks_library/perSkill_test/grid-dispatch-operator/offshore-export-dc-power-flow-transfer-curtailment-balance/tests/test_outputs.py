import json
import os
from itertools import combinations

import numpy as np

INPUT_FILE = os.environ.get("INPUT_FILE", "/root/offshore_snapshot.json")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/wind_export_plan.json")
TOL = 0.05
FEAS_TOL = 1e-6


def load_data():
    assert os.path.exists(INPUT_FILE), f"missing input file: {INPUT_FILE}"
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(INPUT_FILE, encoding="utf-8") as f:
        instance = json.load(f)
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        report = json.load(f)
    return instance, report


def build_network(instance):
    buses = instance["buses"]
    cables = instance["cables"]
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

    return {
        "base_mva": instance["base_mva"],
        "bus_num_to_idx": bus_num_to_idx,
        "non_slack": non_slack,
        "B_reduced_inv": np.linalg.inv(B[np.ix_(non_slack, non_slack)]),
    }


def theta_from_acceptance(instance, network, accepted):
    injections = np.zeros(len(instance["buses"]), dtype=float)
    for value, farm in zip(accepted, instance["wind_farms"]):
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
    n_farm = len(instance["wind_farms"])
    A = []
    b = []

    for idx, farm in enumerate(instance["wind_farms"]):
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
        if np.max(A @ candidate - b) > FEAS_TOL:
            continue
        if len(C) and np.max(np.abs(C @ candidate - d)) > FEAS_TOL:
            continue

        value = float(objective @ candidate)
        if best_obj is None or value > best_obj + FEAS_TOL:
            best_obj = value
            best_x = candidate

    assert best_x is not None, "reference solver found no feasible plan"
    return best_x, best_obj


def reference_solution(instance):
    network = build_network(instance)
    coeffs = flow_matrix(instance, network)
    A, b = build_constraints(instance, coeffs)
    n_farm = len(instance["wind_farms"])

    stage1, total_accepted = solve_vertex_lp(
        A=A,
        b=b,
        objective=np.ones(n_farm, dtype=float),
    )
    assert stage1 is not None

    total_available = sum(farm["available_mw"] for farm in instance["wind_farms"])
    priority_base = int(total_available) + 1
    max_priority = max(farm["curtailment_priority"] for farm in instance["wind_farms"])
    priority_weights = []
    for farm in instance["wind_farms"]:
        exponent = max_priority - farm["curtailment_priority"]
        priority_weights.append(priority_base ** exponent)

    accepted, _ = solve_vertex_lp(
        A=A,
        b=b,
        objective=np.array(priority_weights, dtype=float),
        equalities=[(np.ones(n_farm, dtype=float), total_accepted)],
    )
    flows = coeffs @ accepted
    return accepted, flows


def main():
    instance, report = load_data()
    accepted, flows = reference_solution(instance)

    assert set(report.keys()) == {
        "wind_farm_dispatch",
        "summary",
        "most_congested_cable",
    }, "top-level fields do not match expected structure"

    farms = instance["wind_farms"]
    cables = instance["cables"]
    dispatch = report["wind_farm_dispatch"]
    assert len(dispatch) == len(farms), "wind farm count mismatch"

    dispatch_by_id = {entry["id"]: entry for entry in dispatch}
    expected_acceptance = {farm["id"]: float(accepted[idx]) for idx, farm in enumerate(farms)}

    for farm in farms:
        assert farm["id"] in dispatch_by_id, f"missing wind farm {farm['id']}"
        entry = dispatch_by_id[farm["id"]]
        assert entry["bus"] == farm["bus"], f"wind farm {farm['id']} bus mismatch"
        assert abs(entry["available_MW"] - farm["available_mw"]) <= TOL
        assert abs(entry["accepted_MW"] - expected_acceptance[farm["id"]]) <= TOL
        expected_curtail = entry["available_MW"] - entry["accepted_MW"]
        assert abs(entry["curtailed_MW"] - expected_curtail) <= TOL
        assert -TOL <= entry["accepted_MW"] <= farm["available_mw"] + TOL

    for cable, flow in zip(cables, flows):
        assert abs(flow) <= cable["limit_mw"] + TOL, f"cable {cable['id']} exceeds limit"

    total_available = sum(farm["available_mw"] for farm in farms)
    total_accepted = sum(entry["accepted_MW"] for entry in dispatch)
    total_curtailed = sum(entry["curtailed_MW"] for entry in dispatch)

    summary = report["summary"]
    assert abs(summary["total_available_MW"] - total_available) <= TOL
    assert abs(summary["total_accepted_MW"] - total_accepted) <= TOL
    assert abs(summary["total_curtailed_MW"] - total_curtailed) <= TOL
    assert abs(summary["delivered_to_shore_MW"] - total_accepted) <= TOL
    expected_pct = total_curtailed / total_available * 100.0
    assert abs(summary["curtailment_pct"] - expected_pct) <= 0.1

    loadings = [abs(flow) / cable["limit_mw"] * 100.0 for flow, cable in zip(flows, cables)]
    best_idx = int(np.argmax(loadings))
    expected_cable = cables[best_idx]
    congested = report["most_congested_cable"]
    assert congested["cable_id"] == expected_cable["id"], "wrong congested cable id"
    assert congested["name"] == expected_cable["name"], "wrong congested cable name"
    assert congested["from"] == expected_cable["from"]
    assert congested["to"] == expected_cable["to"]
    assert abs(congested["flow_MW"] - flows[best_idx]) <= TOL
    assert abs(congested["limit_MW"] - expected_cable["limit_mw"]) <= TOL
    assert abs(congested["loading_pct"] - loadings[best_idx]) <= 0.1

    print("validation passed")


if __name__ == "__main__":
    main()
