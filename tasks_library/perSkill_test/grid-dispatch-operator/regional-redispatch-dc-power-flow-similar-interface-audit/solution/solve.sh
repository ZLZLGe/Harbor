#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

INPUT_PATH = Path("/root/redispatch_case.json")
OUTPUT_PATH = Path("/root/redispatch_market_report.json")


def build_b_matrix(buses, branches):
    bus_index = {int(row[0]): idx for idx, row in enumerate(buses)}
    n_bus = len(buses)
    bmat = np.zeros((n_bus, n_bus), dtype=float)
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


def solve_dispatch(case):
    buses = np.array(case["bus"], dtype=float)
    gens = np.array(case["gen"], dtype=float)
    branches = np.array(case["branch"], dtype=float)
    profiles = case["generator_profiles"]
    base_mva = float(case["baseMVA"])

    n_bus = len(buses)
    n_gen = len(gens)
    n_branch = len(branches)

    bmat, bus_index = build_b_matrix(buses, branches)
    load_mw = buses[:, 2]
    slack_idx = next(i for i, row in enumerate(buses) if int(row[1]) == 3)

    n_vars = 3 * n_gen + n_bus
    p_slice = slice(0, n_gen)
    up_slice = slice(n_gen, 2 * n_gen)
    down_slice = slice(2 * n_gen, 3 * n_gen)
    theta_slice = slice(3 * n_gen, 3 * n_gen + n_bus)

    objective = np.zeros(n_vars, dtype=float)
    for i, profile in enumerate(profiles):
        objective[up_slice.start + i] = float(profile["up_bid_dollars_per_MW"])
        objective[down_slice.start + i] = float(profile["down_bid_dollars_per_MW"])

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
        pmin = float(gens[i, 9])
        pmax = float(gens[i, 8])
        lower = max(pmin, baseline - float(profile["ramp_down_MW"]))
        upper = min(pmax, baseline + float(profile["ramp_up_MW"]))
        bounds.append((lower, upper))
    for profile in profiles:
        bounds.append((0.0, float(profile["ramp_up_MW"])))
    for profile in profiles:
        bounds.append((0.0, float(profile["ramp_down_MW"])))
    for _ in range(n_bus):
        bounds.append((None, None))

    result = linprog(
        c=objective,
        A_ub=np.array(a_ub, dtype=float),
        b_ub=np.array(b_ub, dtype=float),
        A_eq=np.array(a_eq, dtype=float),
        b_eq=np.array(b_eq, dtype=float),
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Redispatch optimization failed: {result.message}")

    vector = result.x
    dispatch = vector[p_slice]
    theta = vector[theta_slice]

    line_flows = {}
    constrained_lines = []
    for branch_row in branches:
        f_bus = int(branch_row[0])
        t_bus = int(branch_row[1])
        f = bus_index[f_bus]
        t = bus_index[t_bus]
        x = float(branch_row[3])
        rate = float(branch_row[5])
        flow = base_mva * (1.0 / x) * (theta[f] - theta[t]) if x != 0 else 0.0
        key = (f_bus, t_bus)
        line_flows[key] = flow
        loading = abs(flow) / rate * 100.0 if rate > 0 else 0.0
        if loading >= 85.0 - 1e-9:
            constrained_lines.append(
                {
                    "from": f_bus,
                    "to": t_bus,
                    "flow_MW": round(float(flow), 2),
                    "limit_MW": round(rate, 2),
                    "loading_pct": round(float(loading), 2),
                }
            )

    constrained_lines.sort(key=lambda item: (-item["loading_pct"], item["from"], item["to"]))

    interfaces = []
    for interface in case["interfaces"]:
        flow = 0.0
        for element in interface["elements"]:
            key = (int(element["from"]), int(element["to"]))
            flow += float(element["sign"]) * line_flows[key]
        limit = float(interface["limit_MW"])
        loading = abs(flow) / limit * 100.0 if limit > 0 else 0.0
        interfaces.append(
            {
                "id": interface["id"],
                "flow_MW": round(float(flow), 2),
                "limit_MW": round(limit, 2),
                "loading_pct": round(float(loading), 2),
            }
        )

    interfaces.sort(key=lambda item: (-item["loading_pct"], item["id"]))

    generator_results = []
    for i, profile in enumerate(profiles):
        new_output = float(dispatch[i])
        baseline = float(profile["baseline_output_MW"])
        generator_results.append(
            {
                "id": profile["id"],
                "bus": int(profile["bus"]),
                "baseline_output_MW": round(baseline, 2),
                "new_output_MW": round(new_output, 2),
                "delta_MW": round(new_output - baseline, 2),
                "up_redispatch_price": round(float(profile["up_bid_dollars_per_MW"]), 2),
                "down_redispatch_price": round(float(profile["down_bid_dollars_per_MW"]), 2),
            }
        )

    generator_results.sort(key=lambda item: item["id"])

    report = {
        "case_id": case["case_id"],
        "generator_results": generator_results,
        "interfaces": interfaces,
        "totals": {
            "baseline_generation_MW": round(sum(float(p["baseline_output_MW"]) for p in profiles), 2),
            "redispatched_generation_MW": round(float(np.sum(dispatch)), 2),
            "load_MW": round(float(np.sum(load_mw)), 2),
            "total_redispatch_cost_dollars_per_hour": round(float(result.fun), 2),
        },
        "constrained_lines": constrained_lines,
    }
    return report


with INPUT_PATH.open(encoding="utf-8") as f:
    case_data = json.load(f)

solution = solve_dispatch(case_data)
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(solution, f, indent=2)
PY
