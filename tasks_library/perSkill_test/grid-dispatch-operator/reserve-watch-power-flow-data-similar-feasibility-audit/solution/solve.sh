#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages numpy==1.26.4 -q

python3 <<'PY'
import json
import numpy as np


def round2(value):
    return round(float(value), 2)


with open("/root/network_snapshot.json", encoding="utf-8") as f:
    network = json.load(f)
with open("/root/proposed_schedule.json", encoding="utf-8") as f:
    schedule = json.load(f)

base_mva = float(network["baseMVA"])
buses = np.array(network["bus"], dtype=float)
gens = np.array(network["gen"], dtype=float)
branches = np.array(network["branch"], dtype=float)
reserve_capacity = np.array(network["reserve_capacity"], dtype=float)
schedule_rows = schedule["generator_schedule"]

output_mw = np.array([row["output_MW"] for row in schedule_rows], dtype=float)
reserve_mw = np.array([row["reserve_MW"] for row in schedule_rows], dtype=float)

n_bus = len(buses)
bus_num_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}

B = np.zeros((n_bus, n_bus), dtype=float)
for branch in branches:
    reactance = float(branch[3])
    if reactance == 0:
        continue
    f_idx = bus_num_to_idx[int(branch[0])]
    t_idx = bus_num_to_idx[int(branch[1])]
    susceptance = 1.0 / reactance
    B[f_idx, f_idx] += susceptance
    B[t_idx, t_idx] += susceptance
    B[f_idx, t_idx] -= susceptance
    B[t_idx, f_idx] -= susceptance

load_mw = float(buses[:, 2].sum())
scheduled_generation_mw = float(output_mw.sum())
scheduled_reserve_total_mw = float(reserve_mw.sum())
reserve_requirement_mw = float(network["reserve_requirement"])
generation_minus_load_mw = scheduled_generation_mw - load_mw

reserve_capacity_violations = []
capacity_coupling_violations = []
for i, row in enumerate(schedule_rows):
    bus = int(gens[i, 0])
    reserve_excess = reserve_mw[i] - reserve_capacity[i]
    if reserve_excess > 1e-6:
        reserve_capacity_violations.append(
            {
                "id": int(row["id"]),
                "bus": bus,
                "scheduled_reserve_MW": round2(reserve_mw[i]),
                "reserve_capacity_MW": round2(reserve_capacity[i]),
                "excess_MW": round2(reserve_excess),
            }
        )

    coupling_excess = output_mw[i] + reserve_mw[i] - gens[i, 8]
    if coupling_excess > 1e-6:
        capacity_coupling_violations.append(
            {
                "id": int(row["id"]),
                "bus": bus,
                "scheduled_output_MW": round2(output_mw[i]),
                "scheduled_reserve_MW": round2(reserve_mw[i]),
                "pmax_MW": round2(gens[i, 8]),
                "excess_MW": round2(coupling_excess),
            }
        )

reserve_capacity_violations.sort(key=lambda row: row["id"])
capacity_coupling_violations.sort(key=lambda row: (-row["excess_MW"], row["id"]))

injections_mw = np.zeros(n_bus, dtype=float)
for i, gen in enumerate(gens):
    injections_mw[bus_num_to_idx[int(gen[0])]] += output_mw[i]
injections_mw -= buses[:, 2]

slack_idx = next(i for i, bus in enumerate(buses) if int(bus[1]) == 3)
injections_mw[slack_idx] -= injections_mw.sum()

mask = np.ones(n_bus, dtype=bool)
mask[slack_idx] = False
theta = np.zeros(n_bus, dtype=float)
theta[mask] = np.linalg.solve(B[np.ix_(mask, mask)], injections_mw[mask] / base_mva)

branch_rows = []
for branch in branches:
    f_idx = bus_num_to_idx[int(branch[0])]
    t_idx = bus_num_to_idx[int(branch[1])]
    reactance = float(branch[3])
    rating = float(branch[5])
    flow_mw = 0.0 if reactance == 0 else (1.0 / reactance) * (theta[f_idx] - theta[t_idx]) * base_mva
    loading_pct = 0.0 if rating <= 0 else abs(flow_mw) / rating * 100.0
    branch_rows.append(
        {
            "from": int(branch[0]),
            "to": int(branch[1]),
            "flow_MW": round2(flow_mw),
            "rating_MW": round2(rating),
            "loading_pct": round2(loading_pct),
        }
    )

branch_loading_top3 = sorted(
    branch_rows,
    key=lambda row: (-row["loading_pct"], row["from"], row["to"]),
)[:3]

audit = {
    "checks": {
        "generation_matches_load": round2(scheduled_generation_mw) == round2(load_mw),
        "reserve_requirement_met": scheduled_reserve_total_mw + 1e-6 >= reserve_requirement_mw,
        "all_reserves_within_generator_limits": len(reserve_capacity_violations) == 0,
        "all_generators_within_capacity_coupling": len(capacity_coupling_violations) == 0,
    },
    "totals": {
        "load_MW": round2(load_mw),
        "scheduled_generation_MW": round2(scheduled_generation_mw),
        "generation_minus_load_MW": round2(generation_minus_load_mw),
        "scheduled_reserve_MW": round2(scheduled_reserve_total_mw),
        "reserve_requirement_MW": round2(reserve_requirement_mw),
        "reserve_shortfall_MW": round2(max(reserve_requirement_mw - scheduled_reserve_total_mw, 0.0)),
    },
    "reserve_capacity_violations": reserve_capacity_violations,
    "capacity_coupling_violations": capacity_coupling_violations,
    "branch_loading_top3": branch_loading_top3,
}

with open("/root/dispatch_audit.json", "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2)
PY
