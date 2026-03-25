import json
import os

import numpy as np
import pytest
from scipy.optimize import linprog

CASE_PATH = "/root/redispatch_case.json"
OUTPUT_PATH = "/root/redispatch_market_report.json"
TOL = 1e-2


def build_b_matrix(buses, branches):
    bus_index = {int(row[0]): idx for idx, row in enumerate(buses)}
    bmat = np.zeros((len(buses), len(buses)), dtype=float)
    for row in branches:
        f = bus_index[int(row[0])]
        t = bus_index[int(row[1])]
        x = float(row[3])
        if x == 0:
            continue
        susceptance = 1.0 / x
        bmat[f, f] += susceptance
        bmat[t, t] += susceptance
        bmat[f, t] -= susceptance
        bmat[t, f] -= susceptance
    return bmat, bus_index


def solve_reference(case):
    buses = np.array(case["bus"], dtype=float)
    gens = np.array(case["gen"], dtype=float)
    branches = np.array(case["branch"], dtype=float)
    profiles = case["generator_profiles"]
    base_mva = float(case["baseMVA"])

    n_bus = len(buses)
    n_gen = len(gens)
    bmat, bus_index = build_b_matrix(buses, branches)
    slack_idx = next(i for i, row in enumerate(buses) if int(row[1]) == 3)

    n_vars = 3 * n_gen + n_bus
    p_slice = slice(0, n_gen)
    up_slice = slice(n_gen, 2 * n_gen)
    down_slice = slice(2 * n_gen, 3 * n_gen)
    theta_slice = slice(3 * n_gen, 3 * n_gen + n_bus)

    c = np.zeros(n_vars, dtype=float)
    for i, profile in enumerate(profiles):
        c[up_slice.start + i] = float(profile["up_bid_dollars_per_MW"])
        c[down_slice.start + i] = float(profile["down_bid_dollars_per_MW"])

    a_eq = []
    b_eq = []
    for i, profile in enumerate(profiles):
        row = np.zeros(n_vars, dtype=float)
        row[p_slice.start + i] = 1.0
        row[up_slice.start + i] = -1.0
        row[down_slice.start + i] = 1.0
        a_eq.append(row)
        b_eq.append(float(profile["baseline_output_MW"]))

    for bus_pos, bus_row in enumerate(buses):
        row = np.zeros(n_vars, dtype=float)
        bus_id = int(bus_row[0])
        for gen_pos, profile in enumerate(profiles):
            if int(profile["bus"]) == bus_id:
                row[p_slice.start + gen_pos] += 1.0
        row[theta_slice] = -base_mva * bmat[bus_pos, :]
        a_eq.append(row)
        b_eq.append(float(bus_row[2]))

    row = np.zeros(n_vars, dtype=float)
    row[theta_slice.start + slack_idx] = 1.0
    a_eq.append(row)
    b_eq.append(0.0)

    a_ub = []
    b_ub = []
    for branch_row in branches:
        f = bus_index[int(branch_row[0])]
        t = bus_index[int(branch_row[1])]
        x = float(branch_row[3])
        rate = float(branch_row[5])
        if x == 0 or rate <= 0:
            continue
        coeff = base_mva * (1.0 / x)
        row = np.zeros(n_vars, dtype=float)
        row[theta_slice.start + f] = coeff
        row[theta_slice.start + t] = -coeff
        a_ub.append(row)
        b_ub.append(rate)
        a_ub.append(-row)
        b_ub.append(rate)

    bounds = []
    for i, profile in enumerate(profiles):
        baseline = float(profile["baseline_output_MW"])
        lower = max(float(gens[i, 9]), baseline - float(profile["ramp_down_MW"]))
        upper = min(float(gens[i, 8]), baseline + float(profile["ramp_up_MW"]))
        bounds.append((lower, upper))
    for profile in profiles:
        bounds.append((0.0, float(profile["ramp_up_MW"])))
    for profile in profiles:
        bounds.append((0.0, float(profile["ramp_down_MW"])))
    for _ in range(n_bus):
        bounds.append((None, None))

    result = linprog(
        c=c,
        A_ub=np.array(a_ub, dtype=float),
        b_ub=np.array(b_ub, dtype=float),
        A_eq=np.array(a_eq, dtype=float),
        b_eq=np.array(b_eq, dtype=float),
        bounds=bounds,
        method="highs",
    )
    assert result.success, result.message

    dispatch = result.x[p_slice]
    theta = result.x[theta_slice]

    line_flows = {}
    line_loading = {}
    for branch_row in branches:
        f_bus = int(branch_row[0])
        t_bus = int(branch_row[1])
        f = bus_index[f_bus]
        t = bus_index[t_bus]
        x = float(branch_row[3])
        rate = float(branch_row[5])
        flow = base_mva * (1.0 / x) * (theta[f] - theta[t]) if x != 0 else 0.0
        line_flows[(f_bus, t_bus)] = flow
        line_loading[(f_bus, t_bus)] = abs(flow) / rate * 100.0 if rate > 0 else 0.0

    interface_rows = []
    for interface in case["interfaces"]:
        flow = 0.0
        for element in interface["elements"]:
            flow += float(element["sign"]) * line_flows[(int(element["from"]), int(element["to"]))]
        limit = float(interface["limit_MW"])
        interface_rows.append(
            {
                "id": interface["id"],
                "flow_MW": round(float(flow), 2),
                "limit_MW": round(limit, 2),
                "loading_pct": round(abs(flow) / limit * 100.0, 2),
            }
        )
    interface_rows.sort(key=lambda item: (-item["loading_pct"], item["id"]))

    constrained_rows = []
    for branch_row in branches:
        key = (int(branch_row[0]), int(branch_row[1]))
        loading = line_loading[key]
        if loading >= 85.0 - 1e-9:
            constrained_rows.append(
                {
                    "from": key[0],
                    "to": key[1],
                    "flow_MW": round(float(line_flows[key]), 2),
                    "limit_MW": round(float(branch_row[5]), 2),
                    "loading_pct": round(float(loading), 2),
                }
            )
    constrained_rows.sort(key=lambda item: (-item["loading_pct"], item["from"], item["to"]))

    return {
        "dispatch": dispatch,
        "objective": round(float(result.fun), 2),
        "interfaces": interface_rows,
        "constrained_lines": constrained_rows,
        "total_load": round(float(np.sum(buses[:, 2])), 2),
        "total_base_generation": round(sum(float(p["baseline_output_MW"]) for p in profiles), 2),
        "line_flows": line_flows,
        "bus_index": bus_index,
        "b_matrix": bmat,
    }


@pytest.fixture(scope="module")
def case():
    with open(CASE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_PATH), f"Missing {OUTPUT_PATH}"
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference(case):
    return solve_reference(case)


def test_schema(case, report):
    assert report["case_id"] == case["case_id"]
    assert isinstance(report["generator_results"], list)
    assert isinstance(report["interfaces"], list)
    assert isinstance(report["constrained_lines"], list)
    assert isinstance(report["totals"], dict)

    expected_ids = sorted(profile["id"] for profile in case["generator_profiles"])
    actual_ids = [row["id"] for row in report["generator_results"]]
    assert actual_ids == expected_ids

    for row in report["generator_results"]:
        for key in [
            "id",
            "bus",
            "baseline_output_MW",
            "new_output_MW",
            "delta_MW",
            "up_redispatch_price",
            "down_redispatch_price",
        ]:
            assert key in row

    interface_ids = {row["id"] for row in report["interfaces"]}
    assert interface_ids == {row["id"] for row in case["interfaces"]}
    for row in report["interfaces"]:
        for key in ["id", "flow_MW", "limit_MW", "loading_pct"]:
            assert key in row

    for row in report["constrained_lines"]:
        for key in ["from", "to", "flow_MW", "limit_MW", "loading_pct"]:
            assert key in row

    for key in [
        "baseline_generation_MW",
        "redispatched_generation_MW",
        "load_MW",
        "total_redispatch_cost_dollars_per_hour",
    ]:
        assert key in report["totals"]


def test_redispatch_optimality(case, report, reference):
    profiles = {profile["id"]: profile for profile in case["generator_profiles"]}
    gen_rows = np.array(case["gen"], dtype=float)

    actual_cost = 0.0
    actual_generation = 0.0
    for idx, row in enumerate(report["generator_results"]):
        profile = profiles[row["id"]]
        baseline = float(profile["baseline_output_MW"])
        new_output = float(row["new_output_MW"])
        delta = new_output - baseline
        assert float(row["delta_MW"]) == pytest.approx(delta, abs=TOL)
        assert float(row["baseline_output_MW"]) == pytest.approx(baseline, abs=TOL)
        assert float(row["up_redispatch_price"]) == pytest.approx(float(profile["up_bid_dollars_per_MW"]), abs=TOL)
        assert float(row["down_redispatch_price"]) == pytest.approx(float(profile["down_bid_dollars_per_MW"]), abs=TOL)
        assert int(row["bus"]) == int(profile["bus"])

        lower = max(float(gen_rows[idx, 9]), baseline - float(profile["ramp_down_MW"]))
        upper = min(float(gen_rows[idx, 8]), baseline + float(profile["ramp_up_MW"]))
        assert lower - TOL <= new_output <= upper + TOL

        actual_generation += new_output
        actual_cost += (
            max(delta, 0.0) * float(profile["up_bid_dollars_per_MW"])
            + max(-delta, 0.0) * float(profile["down_bid_dollars_per_MW"])
        )

    assert actual_generation == pytest.approx(reference["total_load"], abs=TOL)
    assert float(report["totals"]["baseline_generation_MW"]) == pytest.approx(reference["total_base_generation"], abs=TOL)
    assert float(report["totals"]["redispatched_generation_MW"]) == pytest.approx(actual_generation, abs=TOL)
    assert float(report["totals"]["load_MW"]) == pytest.approx(reference["total_load"], abs=TOL)
    assert actual_cost == pytest.approx(reference["objective"], abs=TOL)
    assert float(report["totals"]["total_redispatch_cost_dollars_per_hour"]) == pytest.approx(reference["objective"], abs=TOL)


def test_network_and_interfaces(case, report):
    buses = np.array(case["bus"], dtype=float)
    branches = np.array(case["branch"], dtype=float)
    profiles = {profile["id"]: profile for profile in case["generator_profiles"]}
    dispatch_by_bus = {}
    for row in report["generator_results"]:
        dispatch_by_bus.setdefault(int(row["bus"]), 0.0)
        dispatch_by_bus[int(row["bus"])] += float(row["new_output_MW"])

    bmat, bus_index = build_b_matrix(buses, branches)
    slack_idx = next(i for i, row in enumerate(buses) if int(row[1]) == 3)
    injections = np.array(
        [dispatch_by_bus.get(int(bus_row[0]), 0.0) - float(bus_row[2]) for bus_row in buses],
        dtype=float,
    )
    assert injections.sum() == pytest.approx(0.0, abs=TOL)

    reduced = np.delete(np.delete(bmat, slack_idx, axis=0), slack_idx, axis=1)
    rhs = np.delete(injections, slack_idx) / float(case["baseMVA"])
    theta_reduced = np.linalg.solve(reduced, rhs)
    theta = np.insert(theta_reduced, slack_idx, 0.0)

    line_flows = {}
    expected_constrained = []
    for branch_row in branches:
        f_bus = int(branch_row[0])
        t_bus = int(branch_row[1])
        f = bus_index[f_bus]
        t = bus_index[t_bus]
        x = float(branch_row[3])
        rate = float(branch_row[5])
        flow = float(case["baseMVA"]) * (1.0 / x) * (theta[f] - theta[t]) if x != 0 else 0.0
        line_flows[(f_bus, t_bus)] = flow
        loading = abs(flow) / rate * 100.0 if rate > 0 else 0.0
        assert loading <= 100.0 + 1e-5
        if loading >= 85.0 - 1e-9:
            expected_constrained.append(
                {
                    "from": f_bus,
                    "to": t_bus,
                    "flow_MW": round(flow, 2),
                    "limit_MW": round(rate, 2),
                    "loading_pct": round(loading, 2),
                }
            )

    expected_interfaces = []
    for interface in case["interfaces"]:
        flow = 0.0
        for element in interface["elements"]:
            flow += float(element["sign"]) * line_flows[(int(element["from"]), int(element["to"]))]
        limit = float(interface["limit_MW"])
        expected_interfaces.append(
            {
                "id": interface["id"],
                "flow_MW": round(flow, 2),
                "limit_MW": round(limit, 2),
                "loading_pct": round(abs(flow) / limit * 100.0, 2),
            }
        )

    expected_interfaces.sort(key=lambda item: (-item["loading_pct"], item["id"]))
    assert report["interfaces"] == expected_interfaces

    expected_constrained.sort(key=lambda item: (-item["loading_pct"], item["from"], item["to"]))
    assert report["constrained_lines"] == expected_constrained
