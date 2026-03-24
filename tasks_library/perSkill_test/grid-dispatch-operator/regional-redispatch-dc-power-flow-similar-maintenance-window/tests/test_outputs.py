import json
import math
import os
from itertools import combinations

import numpy as np

INPUT_FILE = "/root/maintenance_window.json"
OUTPUT_FILE = "/root/redispatch_report.json"
DISPATCH_TOL = 0.05
ANGLE_TOL = 0.05
FLOW_TOL = 0.05
SUMMARY_TOL = 0.05


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
    lines = instance["lines"]
    reference_bus = instance["reference_bus"]
    base_mva = instance["base_mva"]
    bus_ids = [bus["id"] for bus in buses]
    bus_num_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    slack_idx = bus_num_to_idx[reference_bus]
    n_bus = len(buses)

    B = np.zeros((n_bus, n_bus), dtype=float)
    for line in lines:
        f = bus_num_to_idx[line["from"]]
        t = bus_num_to_idx[line["to"]]
        b = 1.0 / line["reactance_pu"]
        B[f, f] += b
        B[t, t] += b
        B[f, t] -= b
        B[t, f] -= b

    non_slack = [idx for idx in range(n_bus) if idx != slack_idx]
    B_reduced_inv = np.linalg.inv(B[np.ix_(non_slack, non_slack)])
    return base_mva, bus_num_to_idx, slack_idx, non_slack, B_reduced_inv


def theta_from_dispatch(instance, network, dispatch):
    base_mva, bus_num_to_idx, _, non_slack, B_reduced_inv = network
    buses = instance["buses"]
    generators = instance["generators"]
    injections = np.zeros(len(buses), dtype=float)

    for value, gen in zip(dispatch, generators):
        injections[bus_num_to_idx[gen["bus"]]] += value / base_mva
    for bus in buses:
        injections[bus_num_to_idx[bus["id"]]] -= bus["demand_mw"] / base_mva

    theta = np.zeros(len(buses), dtype=float)
    theta[non_slack] = B_reduced_inv @ injections[non_slack]
    return theta


def line_flows(instance, network, theta):
    base_mva, bus_num_to_idx, _, _, _ = network
    flows = []
    for line in instance["lines"]:
        f = bus_num_to_idx[line["from"]]
        t = bus_num_to_idx[line["to"]]
        flows.append((theta[f] - theta[t]) / line["reactance_pu"] * base_mva)
    return np.array(flows, dtype=float)


def affine_flow_model(instance, network):
    n_gen = len(instance["generators"])
    constant = line_flows(instance, network, theta_from_dispatch(instance, network, np.zeros(n_gen)))
    columns = []
    for gen_idx in range(n_gen):
        dispatch = np.zeros(n_gen, dtype=float)
        dispatch[gen_idx] = 1.0
        columns.append(
            line_flows(instance, network, theta_from_dispatch(instance, network, dispatch)) - constant
        )
    return constant, np.column_stack(columns)


def solve_optimal_dispatch(instance, network):
    generators = instance["generators"]
    lines = instance["lines"]
    n_gen = len(generators)
    total_load = sum(bus["demand_mw"] for bus in instance["buses"])
    flow_constant, flow_matrix = affine_flow_model(instance, network)

    inequalities = []
    for gen_idx, gen in enumerate(generators):
        selector = np.zeros(n_gen, dtype=float)
        selector[gen_idx] = 1.0
        inequalities.append((-selector, -gen["min_mw"]))
        inequalities.append((selector, gen["max_mw"]))

    for line_idx, line in enumerate(lines):
        coeffs = flow_matrix[line_idx]
        constant = flow_constant[line_idx]
        inequalities.append((coeffs, line["limit_mw"] - constant))
        inequalities.append((-coeffs, line["limit_mw"] + constant))

    balance = np.ones((1, n_gen), dtype=float)
    rhs_balance = np.array([total_load], dtype=float)

    best_dispatch = None
    best_cost = None
    for active in combinations(range(len(inequalities)), n_gen - 1):
        matrix = np.vstack([balance] + [inequalities[idx][0] for idx in active])
        rhs = np.concatenate([rhs_balance, [inequalities[idx][1] for idx in active]])
        if np.linalg.matrix_rank(matrix) < n_gen:
            continue
        dispatch = np.linalg.solve(matrix, rhs)
        feasible = True
        for coeffs, bound in inequalities:
            if coeffs @ dispatch - bound > 1e-6:
                feasible = False
                break
        if not feasible:
            continue
        cost = float(sum(
            dispatch[idx] * generators[idx]["offer_usd_per_mwh"]
            for idx in range(n_gen)
        ))
        if best_cost is None or cost < best_cost - 1e-8:
            best_cost = cost
            best_dispatch = dispatch

    assert best_dispatch is not None, "no feasible dispatch found in reference solver"
    return best_dispatch, best_cost


def main():
    instance, report = load_data()
    network = build_network(instance)
    optimal_dispatch, optimal_cost = solve_optimal_dispatch(instance, network)
    optimal_theta = theta_from_dispatch(instance, network, optimal_dispatch)
    optimal_flows = line_flows(instance, network, optimal_theta)

    generators = instance["generators"]
    buses = instance["buses"]
    lines = instance["lines"]

    assert set(report.keys()) == {
        "generator_dispatch",
        "bus_angles_deg",
        "summary",
        "most_congested_corridor",
    }, "top-level fields do not match expected structure"

    assert len(report["generator_dispatch"]) == len(generators), "generator count mismatch"
    assert len(report["bus_angles_deg"]) == len(buses), "bus angle count mismatch"

    dispatch_by_id = {entry["id"]: entry for entry in report["generator_dispatch"]}
    angle_by_bus = {entry["bus"]: entry["angle_deg"] for entry in report["bus_angles_deg"]}

    expected_dispatch = {
        gen["id"]: float(optimal_dispatch[idx]) for idx, gen in enumerate(generators)
    }

    for gen in generators:
        assert gen["id"] in dispatch_by_id, f"missing generator {gen['id']}"
        entry = dispatch_by_id[gen["id"]]
        assert entry["bus"] == gen["bus"], f"generator {gen['id']} bus mismatch"
        assert abs(entry["baseline_MW"] - gen["baseline_mw"]) <= SUMMARY_TOL
        assert abs(entry["dispatch_MW"] - expected_dispatch[gen["id"]]) <= DISPATCH_TOL
        expected_delta = entry["dispatch_MW"] - entry["baseline_MW"]
        assert abs(entry["delta_MW"] - expected_delta) <= DISPATCH_TOL
        assert gen["min_mw"] - DISPATCH_TOL <= entry["dispatch_MW"] <= gen["max_mw"] + DISPATCH_TOL

    for bus in buses:
        assert bus["id"] in angle_by_bus, f"missing angle for bus {bus['id']}"
        expected_angle = optimal_theta[[b["id"] for b in buses].index(bus["id"])] * 180.0 / math.pi
        assert abs(angle_by_bus[bus["id"]] - expected_angle) <= ANGLE_TOL

    reference_bus = instance["reference_bus"]
    assert abs(angle_by_bus[reference_bus]) <= ANGLE_TOL, "reference bus angle must be 0"

    reported_generation = sum(entry["dispatch_MW"] for entry in report["generator_dispatch"])
    total_load = sum(bus["demand_mw"] for bus in buses)
    expected_adjustment = sum(
        abs(dispatch_by_id[gen["id"]]["dispatch_MW"] - gen["baseline_mw"])
        for gen in generators
    )

    summary = report["summary"]
    assert abs(summary["total_generation_MW"] - reported_generation) <= SUMMARY_TOL
    assert abs(summary["total_generation_MW"] - total_load) <= SUMMARY_TOL
    assert abs(summary["total_load_MW"] - total_load) <= SUMMARY_TOL
    assert abs(summary["total_cost_usd_per_hour"] - optimal_cost) <= SUMMARY_TOL
    assert abs(summary["total_adjustment_MW"] - expected_adjustment) <= SUMMARY_TOL

    reported_theta = np.zeros(len(buses), dtype=float)
    bus_num_to_idx = {bus["id"]: idx for idx, bus in enumerate(buses)}
    for bus_id, angle_deg in angle_by_bus.items():
        reported_theta[bus_num_to_idx[bus_id]] = angle_deg * math.pi / 180.0
    reported_flows = line_flows(instance, network, reported_theta)

    for line, flow in zip(lines, reported_flows):
        assert abs(flow) <= line["limit_mw"] + FLOW_TOL, f"line {line['id']} exceeds limit"

    loadings = [abs(flow) / line["limit_mw"] * 100.0 for flow, line in zip(optimal_flows, lines)]
    best_idx = int(np.argmax(loadings))
    expected_line = lines[best_idx]
    corridor = report["most_congested_corridor"]
    assert corridor["line_id"] == expected_line["id"], "wrong congested corridor id"
    assert corridor["name"] == expected_line["name"], "wrong congested corridor name"
    assert corridor["from"] == expected_line["from"]
    assert corridor["to"] == expected_line["to"]
    assert abs(corridor["flow_MW"] - optimal_flows[best_idx]) <= FLOW_TOL
    assert abs(corridor["limit_MW"] - expected_line["limit_mw"]) <= SUMMARY_TOL
    assert abs(corridor["loading_pct"] - loadings[best_idx]) <= 0.1

    print("validation passed")


if __name__ == "__main__":
    main()
