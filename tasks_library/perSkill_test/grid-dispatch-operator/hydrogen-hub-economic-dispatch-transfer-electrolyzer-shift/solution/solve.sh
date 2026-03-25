#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

import yaml


SHIFT_FILE = Path("/root/shift_requirements.yaml")
FLEET_FILE = Path("/root/electrolyzer_fleet.csv")
OUTPUT_FILE = Path("/root/electrolyzer_shift.md")


with SHIFT_FILE.open(encoding="utf-8") as f:
    shift = yaml.safe_load(f)

stacks = []
with FLEET_FILE.open(encoding="utf-8") as f:
    for row in csv.DictReader(f):
        stacks.append(
            {
                "stack_id": row["stack_id"],
                "technology": row["technology"],
                "min_load_MW": float(row["min_load_MW"]),
                "max_load_MW": float(row["max_load_MW"]),
                "hydrogen_yield_kg_per_MWh": float(row["hydrogen_yield_kg_per_MWh"]),
                "stack_wear_dollars_per_MWh": float(row["stack_wear_dollars_per_MWh"]),
            }
        )

shift_hours = float(shift["shift_hours"])
power_price = float(shift["power_price_dollars_per_MWh"])
target_hydrogen = float(shift["hydrogen_target_kg"])
site_power_cap = float(shift["site_power_cap_MW"])
required_idle_flexibility = float(shift["required_idle_flexibility_MW"])

total_max_load = sum(stack["max_load_MW"] for stack in stacks)
dispatch_limit = min(site_power_cap, total_max_load - required_idle_flexibility)

scheduled = {stack["stack_id"]: stack["min_load_MW"] for stack in stacks}
base_load = sum(scheduled.values())
if base_load > dispatch_limit + 1e-9:
    raise SystemExit("Minimum stable loads exceed the allowable dispatch limit")

def hydrogen_from_load(stack, load_mw):
    return load_mw * shift_hours * stack["hydrogen_yield_kg_per_MWh"]

base_hydrogen = sum(hydrogen_from_load(stack, scheduled[stack["stack_id"]]) for stack in stacks)
remaining_hydrogen = max(0.0, target_hydrogen - base_hydrogen)
remaining_dispatch_room = dispatch_limit - base_load

ordered_stacks = sorted(
    stacks,
    key=lambda stack: (
        (power_price + stack["stack_wear_dollars_per_MWh"]) / stack["hydrogen_yield_kg_per_MWh"],
        power_price + stack["stack_wear_dollars_per_MWh"],
        stack["stack_id"],
    ),
)

for stack in ordered_stacks:
    if remaining_hydrogen <= 1e-9:
        break

    headroom = stack["max_load_MW"] - scheduled[stack["stack_id"]]
    if headroom <= 1e-9 or remaining_dispatch_room <= 1e-9:
        continue

    hydrogen_per_mw = shift_hours * stack["hydrogen_yield_kg_per_MWh"]
    needed = remaining_hydrogen / hydrogen_per_mw
    add_load = min(headroom, remaining_dispatch_room, needed)

    scheduled[stack["stack_id"]] += add_load
    remaining_hydrogen -= add_load * hydrogen_per_mw
    remaining_dispatch_room -= add_load

if remaining_hydrogen > 1e-6:
    raise SystemExit("Shift target is infeasible with the provided fleet and flexibility limits")

rows = []
total_power = 0.0
achieved_hydrogen = 0.0
total_cost = 0.0
reserved_flexibility = 0.0

for stack in stacks:
    load = scheduled[stack["stack_id"]]
    hydrogen = hydrogen_from_load(stack, load)
    cost = load * shift_hours * (power_price + stack["stack_wear_dollars_per_MWh"])
    headroom = stack["max_load_MW"] - load

    rows.append(
        {
            "stack_id": stack["stack_id"],
            "technology": stack["technology"],
            "scheduled_load_MW": load,
            "hydrogen_kg": hydrogen,
            "stack_cost_dollars": cost,
            "idle_headroom_MW": headroom,
        }
    )

    total_power += load
    achieved_hydrogen += hydrogen
    total_cost += cost
    reserved_flexibility += headroom

def fmt(value):
    return f"{value:.1f}"

lines = [
    "# Hydrogen Hub Shift Dispatch",
    "",
    "## Shift Summary",
    "| field | value |",
    "| --- | --- |",
    f"| hub_name | {shift['hub_name']} |",
    f"| shift_label | {shift['shift_label']} |",
    f"| shift_start | {shift['shift_start']} |",
    f"| shift_hours | {fmt(shift_hours)} |",
    f"| hydrogen_target_kg | {fmt(target_hydrogen)} |",
    f"| site_power_cap_MW | {fmt(site_power_cap)} |",
    f"| required_idle_flexibility_MW | {fmt(required_idle_flexibility)} |",
    "",
    "## Stack Dispatch",
    "| stack_id | technology | scheduled_load_MW | hydrogen_kg | stack_cost_dollars | idle_headroom_MW |",
    "| --- | --- | ---: | ---: | ---: | ---: |",
]

for row in rows:
    lines.append(
        f"| {row['stack_id']} | {row['technology']} | {fmt(row['scheduled_load_MW'])} | "
        f"{fmt(row['hydrogen_kg'])} | {fmt(row['stack_cost_dollars'])} | {fmt(row['idle_headroom_MW'])} |"
    )

lines.extend(
    [
        "",
        "## Totals",
        "| metric | value |",
        "| --- | --- |",
        f"| total_power_MW | {fmt(total_power)} |",
        f"| achieved_hydrogen_kg | {fmt(achieved_hydrogen)} |",
        f"| total_operating_cost_dollars | {fmt(total_cost)} |",
        f"| reserved_flexibility_MW | {fmt(reserved_flexibility)} |",
        "",
    ]
)

OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
PY
