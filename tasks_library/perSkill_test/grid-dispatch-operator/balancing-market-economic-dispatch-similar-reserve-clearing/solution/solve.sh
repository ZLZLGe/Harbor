#!/bin/bash
set -e

pip3 install --break-system-packages numpy==1.26.4 scipy==1.11.4 -q

python3 <<'PY'
import json

from scipy.optimize import linprog

INPUT_FILE = "/root/balancing_market_snapshot.json"
OUTPUT_FILE = "/root/balancing_market_report.json"
TOL = 1e-7


with open(INPUT_FILE, encoding="utf-8") as f:
    snapshot = json.load(f)

units = snapshot["units"]
load = snapshot["load_MW"]
reserve_requirement = snapshot["reserve_requirement_MW"]

block_meta = []
reserve_indices = {}
objective = []
bounds = []

for unit_idx, unit in enumerate(units):
    block_total = 0.0
    for block in unit["energy_blocks"]:
        objective.append(float(block["price"]))
        bounds.append((0.0, float(block["mw"])))
        block_meta.append((unit_idx, float(block["mw"])))
        block_total += float(block["mw"])
    if abs(block_total - float(unit["p_max_MW"])) > 1e-6:
        raise ValueError(f"{unit['unit_id']} energy_blocks must sum to p_max_MW")

for unit_idx, unit in enumerate(units):
    reserve_indices[unit_idx] = len(objective)
    objective.append(float(unit["reserve_offer_dollars_per_MW"]))
    bounds.append((0.0, float(unit["reserve_max_MW"])))

n_vars = len(objective)


def unit_block_indices(target_unit_idx):
    return [idx for idx, (unit_idx, _width) in enumerate(block_meta) if unit_idx == target_unit_idx]


a_eq = []
b_eq = []
energy_balance = [0.0] * n_vars
for idx in range(len(block_meta)):
    energy_balance[idx] = 1.0
a_eq.append(energy_balance)
b_eq.append(load)

a_ub = []
b_ub = []

reserve_requirement_row = [0.0] * n_vars
for unit_idx in range(len(units)):
    reserve_requirement_row[reserve_indices[unit_idx]] = -1.0
a_ub.append(reserve_requirement_row)
b_ub.append(-reserve_requirement)

for unit_idx, unit in enumerate(units):
    block_indices = unit_block_indices(unit_idx)

    min_row = [0.0] * n_vars
    for idx in block_indices:
        min_row[idx] = -1.0
    a_ub.append(min_row)
    b_ub.append(-float(unit["p_min_MW"]))

    coupling_row = [0.0] * n_vars
    for idx in block_indices:
        coupling_row[idx] = 1.0
    coupling_row[reserve_indices[unit_idx]] = 1.0
    a_ub.append(coupling_row)
    b_ub.append(float(unit["p_max_MW"]))

result = linprog(
    c=objective,
    A_ub=a_ub,
    b_ub=b_ub,
    A_eq=a_eq,
    b_eq=b_eq,
    bounds=bounds,
    method="highs",
)

if not result.success:
    raise RuntimeError(f"Optimization failed: {result.message}")

solution = result.x
unit_dispatch = []
tight_units = []
uncommitted_capacity = 0.0

for unit_idx, unit in enumerate(units):
    energy = sum(solution[idx] for idx in unit_block_indices(unit_idx))
    reserve = solution[reserve_indices[unit_idx]]
    headroom = float(unit["p_max_MW"]) - energy - reserve
    if abs(headroom) <= TOL:
        headroom = 0.0

    unit_dispatch.append(
        {
            "unit_id": unit["unit_id"],
            "energy_MW": round(float(energy), 4),
            "reserve_MW": round(float(reserve), 4),
            "headroom_MW": round(float(headroom), 4),
            "p_max_MW": round(float(unit["p_max_MW"]), 4),
        }
    )
    uncommitted_capacity += max(headroom, 0.0)

    if headroom == 0.0:
        tight_units.append(
            {
                "unit_id": unit["unit_id"],
                "binding_reason": "energy_plus_reserve_hits_pmax",
                "headroom_MW": 0.0,
            }
        )

tight_units.sort(key=lambda item: item["unit_id"])

report = {
    "market_id": snapshot["market_id"],
    "unit_dispatch": unit_dispatch,
    "totals": {
        "load_MW": round(float(load), 4),
        "energy_cleared_MW": round(sum(item["energy_MW"] for item in unit_dispatch), 4),
        "reserve_requirement_MW": round(float(reserve_requirement), 4),
        "reserve_cleared_MW": round(sum(item["reserve_MW"] for item in unit_dispatch), 4),
        "total_cost_dollars_per_hour": round(float(result.fun), 4),
    },
    "marginal_tight_units": tight_units,
    "uncommitted_capacity_MW": round(float(uncommitted_capacity), 4),
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
    f.write("\n")

print(json.dumps(report, indent=2))
PY
