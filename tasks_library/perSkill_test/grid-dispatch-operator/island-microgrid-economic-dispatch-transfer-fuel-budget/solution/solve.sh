#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json

INPUT_REQUIREMENTS = "/root/dispatch_requirements.json"
INPUT_FLEET = "/root/generator_fleet.csv"
INPUT_LOAD = "/root/hourly_load.csv"
OUTPUT_FILE = "/root/microgrid_schedule.csv"
EPS = 1e-9


def read_inputs():
    with open(INPUT_REQUIREMENTS, encoding="utf-8") as f:
        requirements = json.load(f)

    with open(INPUT_FLEET, encoding="utf-8") as f:
        units = []
        for row in csv.DictReader(f):
            units.append({
                "unit_id": row["unit_id"],
                "min_output_MW": float(row["min_output_MW"]),
                "max_output_MW": float(row["max_output_MW"]),
                "variable_cost_dollars_per_MWh": float(row["variable_cost_dollars_per_MWh"]),
                "fuel_burn_liters_per_MWh": float(row["fuel_burn_liters_per_MWh"]),
            })

    with open(INPUT_LOAD, encoding="utf-8") as f:
        loads = []
        for row in csv.DictReader(f):
            loads.append({
                "hour": int(row["hour"]),
                "load_MW": float(row["load_MW"]),
            })

    return requirements, units, loads


def order_units(units, lam, tie_break):
    if tie_break == "cheap_first":
        return sorted(
            units,
            key=lambda unit: (
                unit["variable_cost_dollars_per_MWh"] + lam * unit["fuel_burn_liters_per_MWh"],
                unit["variable_cost_dollars_per_MWh"],
                -unit["fuel_burn_liters_per_MWh"],
                unit["unit_id"],
            ),
        )

    return sorted(
        units,
        key=lambda unit: (
            unit["variable_cost_dollars_per_MWh"] + lam * unit["fuel_burn_liters_per_MWh"],
            unit["fuel_burn_liters_per_MWh"],
            unit["variable_cost_dollars_per_MWh"],
            unit["unit_id"],
        ),
    )


def build_schedule(units, loads, lam, tie_break):
    base_output = sum(unit["min_output_MW"] for unit in units)
    ordered_units = order_units(units, lam, tie_break)
    rows = []
    total_cost = 0.0
    total_fuel = 0.0
    cumulative_fuel = 0.0

    for load_row in loads:
        remaining = load_row["load_MW"] - base_output
        dispatch = {unit["unit_id"]: unit["min_output_MW"] for unit in units}

        if remaining < -EPS:
            raise ValueError("Infeasible load below aggregate minimum output")

        for unit in ordered_units:
            headroom = unit["max_output_MW"] - unit["min_output_MW"]
            take = min(headroom, max(0.0, remaining))
            dispatch[unit["unit_id"]] += take
            remaining -= take
            if remaining <= EPS:
                break

        if remaining > 1e-6:
            raise ValueError("Infeasible load above aggregate maximum output")

        hourly_generation = 0.0
        hourly_fuel = 0.0
        hourly_cost = 0.0
        row = {
            "hour": float(load_row["hour"]),
            "load_MW": load_row["load_MW"],
        }

        for unit in units:
            output = dispatch[unit["unit_id"]]
            hourly_generation += output
            hourly_fuel += output * unit["fuel_burn_liters_per_MWh"]
            hourly_cost += output * unit["variable_cost_dollars_per_MWh"]
            row[f"{unit['unit_id']}_MW"] = output

        cumulative_fuel += hourly_fuel
        row["total_generation_MW"] = hourly_generation
        row["hourly_fuel_liters"] = hourly_fuel
        row["cumulative_fuel_liters"] = cumulative_fuel
        rows.append(row)
        total_cost += hourly_cost
        total_fuel += hourly_fuel

    return {
        "rows": rows,
        "total_cost": total_cost,
        "total_fuel": total_fuel,
    }


def breakpoints(units):
    values = []
    for i, left in enumerate(units):
        for right in units[i + 1:]:
            fuel_gap = left["fuel_burn_liters_per_MWh"] - right["fuel_burn_liters_per_MWh"]
            if abs(fuel_gap) <= EPS:
                continue
            lam = (
                right["variable_cost_dollars_per_MWh"] - left["variable_cost_dollars_per_MWh"]
            ) / fuel_gap
            if lam > EPS:
                values.append(lam)
    return sorted(set(values))


def blend_schedules(high_fuel_schedule, low_fuel_schedule, target_fuel, units):
    high_fuel = high_fuel_schedule["total_fuel"]
    low_fuel = low_fuel_schedule["total_fuel"]
    if abs(high_fuel - low_fuel) <= EPS:
        return high_fuel_schedule

    alpha = (high_fuel - target_fuel) / (high_fuel - low_fuel)
    blended_rows = []
    cumulative_fuel = 0.0
    total_cost = 0.0

    for high_row, low_row in zip(high_fuel_schedule["rows"], low_fuel_schedule["rows"]):
        row = {
            "hour": high_row["hour"],
            "load_MW": high_row["load_MW"],
        }
        hourly_generation = 0.0
        hourly_fuel = 0.0
        hourly_cost = 0.0

        for unit in units:
            key = f"{unit['unit_id']}_MW"
            output = (1.0 - alpha) * high_row[key] + alpha * low_row[key]
            row[key] = output
            hourly_generation += output
            hourly_fuel += output * unit["fuel_burn_liters_per_MWh"]
            hourly_cost += output * unit["variable_cost_dollars_per_MWh"]

        cumulative_fuel += hourly_fuel
        row["total_generation_MW"] = hourly_generation
        row["hourly_fuel_liters"] = hourly_fuel
        row["cumulative_fuel_liters"] = cumulative_fuel
        blended_rows.append(row)
        total_cost += hourly_cost

    return {
        "rows": blended_rows,
        "total_cost": total_cost,
        "total_fuel": cumulative_fuel,
    }


def solve(requirements, units, loads):
    fuel_budget = float(requirements["daily_fuel_budget_liters"])
    unconstrained = build_schedule(units, loads, lam=0.0, tie_break="cheap_first")
    if unconstrained["total_fuel"] <= fuel_budget + 1e-6:
        return unconstrained

    for lam in breakpoints(units):
        high_fuel = build_schedule(units, loads, lam=lam, tie_break="cheap_first")
        low_fuel = build_schedule(units, loads, lam=lam, tie_break="efficient_first")
        if low_fuel["total_fuel"] - 1e-6 <= fuel_budget <= high_fuel["total_fuel"] + 1e-6:
            return blend_schedules(high_fuel, low_fuel, fuel_budget, units)

    raise ValueError("Fuel budget is infeasible for the provided fleet and load")


def write_csv(rows, units):
    fieldnames = ["hour", "load_MW"]
    fieldnames.extend(f"{unit['unit_id']}_MW" for unit in units)
    fieldnames.extend(["total_generation_MW", "hourly_fuel_liters", "cumulative_fuel_liters"])

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialized = {}
            for key in fieldnames:
                value = row[key]
                if key == "hour":
                    serialized[key] = int(round(value))
                else:
                    serialized[key] = f"{value:.6f}".rstrip("0").rstrip(".")
            writer.writerow(serialized)


requirements, units, loads = read_inputs()
solution = solve(requirements, units, loads)
write_csv(solution["rows"], units)
PY
