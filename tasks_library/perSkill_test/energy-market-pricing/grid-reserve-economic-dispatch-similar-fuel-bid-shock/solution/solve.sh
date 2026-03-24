#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from pathlib import Path


def resolve_input_path() -> Path:
    for candidate in [
        Path("/root/fleet_data.json"),
        Path("fleet_data.json"),
        Path("environment/fleet_data.json"),
    ]:
        try:
            if candidate.exists():
                return candidate
        except PermissionError:
            continue
    raise FileNotFoundError("fleet_data.json not found")


def resolve_output_path() -> Path:
    root_output = Path("/root/dispatch_impact.json")
    if root_output.parent.exists() and os.access(root_output.parent, os.W_OK):
        return root_output
    return Path("dispatch_impact.json")


def merit_order(generators):
    return sorted(
        generators,
        key=lambda gen: (-gen["energy_bid_dollars_per_mwh"], gen["generator_id"]),
    )


def solve_dispatch(generators, load_mw, reserve_requirement_mw):
    total_capacity = sum(gen["pmax_mw"] for gen in generators)
    total_headroom = total_capacity - load_mw

    if total_headroom < 0:
        raise ValueError("Load exceeds total fleet capacity")

    headroom = {gen["generator_id"]: 0.0 for gen in generators}
    remaining_reserve = reserve_requirement_mw

    for gen in merit_order(generators):
        headroom_cap = gen["pmax_mw"] - gen["pmin_mw"]
        reserve_cap = min(gen["reserve_cap_mw"], headroom_cap)
        allocate = min(remaining_reserve, reserve_cap)
        headroom[gen["generator_id"]] += allocate
        remaining_reserve -= allocate

    if remaining_reserve > 1e-9:
        raise ValueError("Reserve requirement is infeasible")

    counted_headroom = sum(headroom.values())
    remaining_headroom = total_headroom - counted_headroom

    if remaining_headroom < -1e-9:
        raise ValueError("Load and reserve requirement are jointly infeasible")

    for gen in merit_order(generators):
        gen_id = gen["generator_id"]
        headroom_cap = gen["pmax_mw"] - gen["pmin_mw"]
        available_extra = headroom_cap - headroom[gen_id]
        allocate = min(remaining_headroom, available_extra)
        if allocate > 0:
            headroom[gen_id] += allocate
            remaining_headroom -= allocate

    if remaining_headroom > 1e-9:
        raise ValueError("Headroom allocation failed")

    reserve_awards = {gen["generator_id"]: 0.0 for gen in generators}
    remaining_reserve = reserve_requirement_mw
    for gen in merit_order(generators):
        gen_id = gen["generator_id"]
        feasible_reserve = min(gen["reserve_cap_mw"], headroom[gen_id])
        allocate = min(remaining_reserve, feasible_reserve)
        reserve_awards[gen_id] = allocate
        remaining_reserve -= allocate

    awards = []
    total_cost = 0.0
    for gen in generators:
        gen_id = gen["generator_id"]
        energy_mw = gen["pmax_mw"] - headroom[gen_id]
        reserve_mw = reserve_awards[gen_id]
        total_cost += gen["energy_bid_dollars_per_mwh"] * energy_mw
        awards.append(
            {
                "generator_id": gen_id,
                "energy_mw": round(energy_mw, 2),
                "reserve_mw": round(reserve_mw, 2),
            }
        )

    return {
        "total_production_cost_dollars_per_hour": round(total_cost, 2),
        "generator_awards": awards,
    }


def scenario_result(generators, load_mw, reserve_requirement_mw):
    base_solution = solve_dispatch(generators, load_mw, reserve_requirement_mw)
    load_plus_one = solve_dispatch(generators, load_mw + 1.0, reserve_requirement_mw)
    reserve_plus_one = solve_dispatch(generators, load_mw, reserve_requirement_mw + 1.0)

    return {
        "total_production_cost_dollars_per_hour": base_solution[
            "total_production_cost_dollars_per_hour"
        ],
        "system_energy_price_dollars_per_mwh": round(
            load_plus_one["total_production_cost_dollars_per_hour"]
            - base_solution["total_production_cost_dollars_per_hour"],
            2,
        ),
        "reserve_mcp_dollars_per_mw": round(
            reserve_plus_one["total_production_cost_dollars_per_hour"]
            - base_solution["total_production_cost_dollars_per_hour"],
            2,
        ),
        "generator_awards": base_solution["generator_awards"],
    }


def apply_counterfactual(data):
    generators = [dict(gen) for gen in data["generators"]]
    target = data["counterfactual"]["generator_id"]
    new_bid = data["counterfactual"]["new_energy_bid_dollars_per_mwh"]

    for gen in generators:
        if gen["generator_id"] == target:
            gen["energy_bid_dollars_per_mwh"] = new_bid
            return generators

    raise ValueError(f"Counterfactual generator {target} not found")


def build_impact(base_case, counterfactual):
    base_awards = {
        entry["generator_id"]: entry for entry in base_case["generator_awards"]
    }
    counter_awards = {
        entry["generator_id"]: entry for entry in counterfactual["generator_awards"]
    }

    redispatch = []
    for generator_id, base_entry in base_awards.items():
        counter_entry = counter_awards[generator_id]
        energy_delta = round(
            counter_entry["energy_mw"] - base_entry["energy_mw"],
            2,
        )
        reserve_delta = round(
            counter_entry["reserve_mw"] - base_entry["reserve_mw"],
            2,
        )
        redispatch.append(
            {
                "generator_id": generator_id,
                "base_energy_mw": base_entry["energy_mw"],
                "counterfactual_energy_mw": counter_entry["energy_mw"],
                "energy_delta_mw": energy_delta,
                "base_reserve_mw": base_entry["reserve_mw"],
                "counterfactual_reserve_mw": counter_entry["reserve_mw"],
                "reserve_delta_mw": reserve_delta,
            }
        )

    redispatch.sort(
        key=lambda entry: (
            -abs(entry["energy_delta_mw"]),
            entry["generator_id"],
        )
    )

    return {
        "cost_change_dollars_per_hour": round(
            counterfactual["total_production_cost_dollars_per_hour"]
            - base_case["total_production_cost_dollars_per_hour"],
            2,
        ),
        "largest_redispatch_units": redispatch[:2],
    }


with resolve_input_path().open(encoding="utf-8") as fh:
    fleet_data = json.load(fh)

base_case = scenario_result(
    fleet_data["generators"],
    fleet_data["load_mw"],
    fleet_data["reserve_requirement_mw"],
)
counterfactual = scenario_result(
    apply_counterfactual(fleet_data),
    fleet_data["load_mw"],
    fleet_data["reserve_requirement_mw"],
)

output = {
    "base_case": base_case,
    "counterfactual": counterfactual,
    "impact_analysis": build_impact(base_case, counterfactual),
}

with resolve_output_path().open("w", encoding="utf-8") as fh:
    json.dump(output, fh, indent=2)
    fh.write("\n")
PY
