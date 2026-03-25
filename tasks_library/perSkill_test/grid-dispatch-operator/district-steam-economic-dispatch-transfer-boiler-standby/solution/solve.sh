#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import tomllib

INPUT_PROFILE = "/root/station_request.toml"
INPUT_FLEET = "/root/boiler_fleet.csv"
OUTPUT_FILE = "/root/steam_commitment.toml"


def read_inputs():
    with open(INPUT_PROFILE, "rb") as f:
        profile = tomllib.load(f)

    boilers = []
    with open(INPUT_FLEET, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            boilers.append(
                {
                    "boiler_id": row["boiler_id"],
                    "boiler_class": row["boiler_class"],
                    "min_steam_klb_per_hr": float(row["min_steam_klb_per_hr"]),
                    "max_steam_klb_per_hr": float(row["max_steam_klb_per_hr"]),
                    "standby_cap_klb_per_hr": float(row["standby_cap_klb_per_hr"]),
                    "incremental_heat_rate_mmbtu_per_klb": float(row["incremental_heat_rate_mmbtu_per_klb"]),
                    "standby_cost_dollars_per_klb": float(row["standby_cost_dollars_per_klb"]),
                }
            )

    return profile, boilers


def enumerate_options(boiler, step, fuel_price):
    headroom_steps = int(round((boiler["max_steam_klb_per_hr"] - boiler["min_steam_klb_per_hr"]) / step))
    standby_cap_steps = int(round(boiler["standby_cap_klb_per_hr"] / step))
    options = []

    for extra_steps in range(headroom_steps + 1):
        standby_limit = min(standby_cap_steps, headroom_steps - extra_steps)
        for standby_steps in range(standby_limit + 1):
            extra_steam = extra_steps * step
            standby = standby_steps * step
            cost = (
                extra_steam * boiler["incremental_heat_rate_mmbtu_per_klb"] * fuel_price
                + standby * boiler["standby_cost_dollars_per_klb"]
            )
            options.append((extra_steps, standby_steps, cost))

    return options


def solve_commitment(profile, boilers):
    step = float(profile["dispatch_step_klb_per_hr"])
    fuel_price = float(profile["fuel_price_dollars_per_mmbtu"])
    base_steam = sum(boiler["min_steam_klb_per_hr"] for boiler in boilers)
    steam_target_steps = int(round((float(profile["steam_demand_klb_per_hr"]) - base_steam) / step))
    standby_target_steps = int(round(float(profile["standby_requirement_klb_per_hr"]) / step))

    states = {(0, 0): (0.0, [])}

    for boiler in boilers:
        options = enumerate_options(boiler, step, fuel_price)
        next_states = {}

        for (steam_steps, standby_steps), (cost_so_far, plan_so_far) in states.items():
            for extra_steps, reserve_steps, add_cost in options:
                new_steam_steps = steam_steps + extra_steps
                new_standby_steps = standby_steps + reserve_steps
                if new_steam_steps > steam_target_steps or new_standby_steps > standby_target_steps:
                    continue

                new_cost = cost_so_far + add_cost
                new_plan = plan_so_far + [(extra_steps, reserve_steps)]
                incumbent = next_states.get((new_steam_steps, new_standby_steps))
                if incumbent is None or new_cost < incumbent[0] - 1e-9:
                    next_states[(new_steam_steps, new_standby_steps)] = (new_cost, new_plan)

        states = next_states

    total_variable_cost, plan = states[(steam_target_steps, standby_target_steps)]
    del total_variable_cost

    commitments = []
    total_fuel_cost = 0.0
    total_standby_cost = 0.0
    total_steam = 0.0
    total_standby = 0.0
    total_margin = 0.0

    for boiler, (extra_steps, standby_steps) in zip(boilers, plan):
        steam = boiler["min_steam_klb_per_hr"] + extra_steps * step
        standby = standby_steps * step
        fuel_cost = steam * boiler["incremental_heat_rate_mmbtu_per_klb"] * fuel_price
        standby_cost = standby * boiler["standby_cost_dollars_per_klb"]
        margin = boiler["max_steam_klb_per_hr"] - steam - standby

        commitments.append(
            {
                "boiler_id": boiler["boiler_id"],
                "boiler_class": boiler["boiler_class"],
                "steam_klb_per_hr": steam,
                "standby_klb_per_hr": standby,
                "idle_headroom_klb_per_hr": margin,
                "fuel_cost_dollars_per_hour": fuel_cost,
                "standby_cost_dollars_per_hour": standby_cost,
            }
        )

        total_steam += steam
        total_standby += standby
        total_fuel_cost += fuel_cost
        total_standby_cost += standby_cost
        total_margin += margin

    totals = {
        "steam_demand_klb_per_hr": float(profile["steam_demand_klb_per_hr"]),
        "steam_dispatched_klb_per_hr": total_steam,
        "standby_requirement_klb_per_hr": float(profile["standby_requirement_klb_per_hr"]),
        "standby_allocated_klb_per_hr": total_standby,
        "total_fuel_cost_dollars_per_hour": total_fuel_cost,
        "total_standby_cost_dollars_per_hour": total_standby_cost,
        "total_operating_cost_dollars_per_hour": total_fuel_cost + total_standby_cost,
        "remaining_standby_margin_klb_per_hr": total_margin,
    }

    return commitments, totals


def format_number(value):
    return f"{value:.3f}"


def write_toml(profile, commitments, totals):
    lines = [
        f'station_name = "{profile["station_name"]}"',
        f'interval_start = "{profile["interval_start"]}"',
        "",
    ]

    for commitment in commitments:
        lines.extend(
            [
                "[[boiler_commitment]]",
                f'boiler_id = "{commitment["boiler_id"]}"',
                f'boiler_class = "{commitment["boiler_class"]}"',
                f'steam_klb_per_hr = {format_number(commitment["steam_klb_per_hr"])}',
                f'standby_klb_per_hr = {format_number(commitment["standby_klb_per_hr"])}',
                f'idle_headroom_klb_per_hr = {format_number(commitment["idle_headroom_klb_per_hr"])}',
                f'fuel_cost_dollars_per_hour = {format_number(commitment["fuel_cost_dollars_per_hour"])}',
                f'standby_cost_dollars_per_hour = {format_number(commitment["standby_cost_dollars_per_hour"])}',
                "",
            ]
        )

    lines.append("[totals]")
    for key, value in totals.items():
        lines.append(f"{key} = {format_number(value)}")
    lines.append("")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


profile, boilers = read_inputs()
commitments, totals = solve_commitment(profile, boilers)
write_toml(profile, commitments, totals)
PY
