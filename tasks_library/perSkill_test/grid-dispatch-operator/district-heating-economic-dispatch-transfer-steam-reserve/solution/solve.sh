#!/bin/bash
set -e

python3 <<'PY'
import json

INPUT_FILE = "/root/steam_station_snapshot.json"
OUTPUT_FILE = "/root/steam_dispatch_report.json"


def validate_blocks(asset, step):
    total_block_steam = 0
    for block in asset["fuel_cost_blocks"]:
        steam = int(block["steam_tph"])
        if steam % step != 0:
            raise ValueError(f"{asset['asset_id']} block steam must align with dispatch_step_tph")
        total_block_steam += steam
    if total_block_steam != int(asset["steam_max_tph"]):
        raise ValueError(f"{asset['asset_id']} fuel_cost_blocks must sum to steam_max_tph")


def build_energy_costs(asset, step):
    validate_blocks(asset, step)
    max_steam = int(asset["steam_max_tph"])
    costs = {0: 0.0}
    running_cost = 0.0
    scheduled_steam = 0

    for block in asset["fuel_cost_blocks"]:
        block_steps = int(block["steam_tph"]) // step
        marginal_cost = float(block["marginal_cost_dollars_per_tph"])
        for _ in range(block_steps):
            scheduled_steam += step
            running_cost += step * marginal_cost
            costs[scheduled_steam] = running_cost

    if scheduled_steam != max_steam:
        raise ValueError(f"{asset['asset_id']} invalid cost curve coverage")
    return costs


def solve_dispatch(snapshot):
    step = int(snapshot["dispatch_step_tph"])
    if step <= 0:
        raise ValueError("dispatch_step_tph must be positive")

    demand = int(snapshot["steam_demand_tph"])
    reserve_requirement = int(snapshot["hot_reserve_requirement_tph"])
    if demand % step != 0 or reserve_requirement % step != 0:
        raise ValueError("Demand and reserve requirement must align with dispatch_step_tph")

    assets = snapshot["assets"]
    dp = {(0, 0): 0.0}
    parents = []

    for asset in assets:
        min_steam = int(asset["steam_min_tph"])
        max_steam = int(asset["steam_max_tph"])
        reserve_cap = int(asset["hot_reserve_max_tph"])
        reserve_cost = float(asset["hot_reserve_cost_dollars_per_tph"])

        if min_steam % step != 0 or max_steam % step != 0 or reserve_cap % step != 0:
            raise ValueError(f"{asset['asset_id']} values must align with dispatch_step_tph")

        energy_costs = build_energy_costs(asset, step)
        options = []
        for steam in range(min_steam, max_steam + step, step):
            if steam not in energy_costs:
                raise ValueError(f"{asset['asset_id']} missing energy cost for {steam} tph")
            usable_reserve = min(reserve_cap, max_steam - steam)
            base_cost = energy_costs[steam]
            for reserve in range(0, usable_reserve + step, step):
                total_cost = base_cost + reserve * reserve_cost
                options.append((steam, reserve, total_cost))

        next_dp = {}
        parent = {}
        for (steam_total, reserve_total), total_cost in dp.items():
            for steam, reserve, option_cost in options:
                new_steam = steam_total + steam
                if new_steam > demand:
                    continue
                new_reserve = min(reserve_requirement, reserve_total + reserve)
                state = (new_steam, new_reserve)
                candidate_cost = total_cost + option_cost
                if candidate_cost < next_dp.get(state, float("inf")) - 1e-9:
                    next_dp[state] = candidate_cost
                    parent[state] = ((steam_total, reserve_total), (steam, reserve))
        dp = next_dp
        parents.append(parent)

    terminal_state = (demand, reserve_requirement)
    if terminal_state not in dp:
        raise RuntimeError("No feasible dispatch found")

    decisions = []
    state = terminal_state
    for parent in reversed(parents):
        previous_state, choice = parent[state]
        decisions.append(choice)
        state = previous_state
    decisions.reverse()

    asset_dispatch = []
    technology_totals = {}
    fully_committed_assets = []

    for asset, (steam, reserve) in zip(assets, decisions):
        spare_headroom = int(asset["steam_max_tph"]) - steam - reserve
        dispatch_row = {
            "asset_id": asset["asset_id"],
            "asset_type": asset["asset_type"],
            "steam_output_tph": round(float(steam), 4),
            "hot_reserve_tph": round(float(reserve), 4),
            "spare_headroom_tph": round(float(spare_headroom), 4),
        }
        asset_dispatch.append(dispatch_row)

        bucket = technology_totals.setdefault(
            asset["asset_type"],
            {"steam_output_tph": 0.0, "hot_reserve_tph": 0.0, "spare_headroom_tph": 0.0},
        )
        bucket["steam_output_tph"] += steam
        bucket["hot_reserve_tph"] += reserve
        bucket["spare_headroom_tph"] += spare_headroom

        if spare_headroom == 0:
            fully_committed_assets.append(asset["asset_id"])

    total_steam = sum(item["steam_output_tph"] for item in asset_dispatch)
    total_reserve = sum(item["hot_reserve_tph"] for item in asset_dispatch)
    total_cost = dp[terminal_state]

    report = {
        "station_id": snapshot["station_id"],
        "asset_dispatch": asset_dispatch,
        "summary": {
            "steam_demand_tph": round(float(demand), 4),
            "steam_scheduled_tph": round(float(total_steam), 4),
            "hot_reserve_requirement_tph": round(float(reserve_requirement), 4),
            "hot_reserve_scheduled_tph": round(float(total_reserve), 4),
            "total_fuel_cost_dollars_per_hour": round(float(total_cost), 4),
            "average_fuel_cost_dollars_per_ton": round(float(total_cost / demand), 4),
        },
        "technology_totals": [
            {
                "asset_type": asset_type,
                "steam_output_tph": round(values["steam_output_tph"], 4),
                "hot_reserve_tph": round(values["hot_reserve_tph"], 4),
                "spare_headroom_tph": round(values["spare_headroom_tph"], 4),
            }
            for asset_type, values in sorted(technology_totals.items())
        ],
        "fully_committed_assets": sorted(fully_committed_assets),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(json.dumps(report, indent=2))


with open(INPUT_FILE, encoding="utf-8") as f:
    solve_dispatch(json.load(f))
PY
