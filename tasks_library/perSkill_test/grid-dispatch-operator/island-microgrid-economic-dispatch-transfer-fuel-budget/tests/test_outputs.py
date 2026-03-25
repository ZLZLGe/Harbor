import csv
import json
import os

INPUT_REQUIREMENTS = "/root/dispatch_requirements.json"
INPUT_FLEET = "/root/generator_fleet.csv"
INPUT_LOAD = "/root/hourly_load.csv"
OUTPUT_FILE = "/root/microgrid_schedule.csv"
EPS = 1e-6


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


def read_output():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
        assert remaining >= -EPS, "Input load is infeasible below aggregate minimum output"

        for unit in ordered_units:
            headroom = unit["max_output_MW"] - unit["min_output_MW"]
            take = min(headroom, max(0.0, remaining))
            dispatch[unit["unit_id"]] += take
            remaining -= take
            if remaining <= EPS:
                break

        assert remaining <= 1e-6, "Input load is infeasible above aggregate maximum output"

        row = {
            "hour": load_row["hour"],
            "load_MW": load_row["load_MW"],
        }
        hourly_generation = 0.0
        hourly_fuel = 0.0
        hourly_cost = 0.0

        for unit in units:
            key = f"{unit['unit_id']}_MW"
            output = dispatch[unit["unit_id"]]
            row[key] = output
            hourly_generation += output
            hourly_fuel += output * unit["fuel_burn_liters_per_MWh"]
            hourly_cost += output * unit["variable_cost_dollars_per_MWh"]

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
    for index, left in enumerate(units):
        for right in units[index + 1:]:
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
    rows = []
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
        rows.append(row)
        total_cost += hourly_cost

    return {
        "rows": rows,
        "total_cost": total_cost,
        "total_fuel": cumulative_fuel,
    }


def optimal_reference(requirements, units, loads):
    fuel_budget = float(requirements["daily_fuel_budget_liters"])
    unconstrained = build_schedule(units, loads, lam=0.0, tie_break="cheap_first")
    if unconstrained["total_fuel"] <= fuel_budget + 1e-6:
        return unconstrained

    for lam in breakpoints(units):
        high_fuel = build_schedule(units, loads, lam=lam, tie_break="cheap_first")
        low_fuel = build_schedule(units, loads, lam=lam, tie_break="efficient_first")
        if low_fuel["total_fuel"] - 1e-6 <= fuel_budget <= high_fuel["total_fuel"] + 1e-6:
            return blend_schedules(high_fuel, low_fuel, fuel_budget, units)

    raise AssertionError("Fuel budget is infeasible for the provided fleet and load")


def to_float(row, key):
    return float(row[key])


def total_reported_cost(output_rows, units):
    unit_map = {unit["unit_id"]: unit for unit in units}
    total_cost = 0.0
    for row in output_rows:
        for unit_id, unit in unit_map.items():
            total_cost += to_float(row, f"{unit_id}_MW") * unit["variable_cost_dollars_per_MWh"]
    return total_cost


def test_schema_and_row_count():
    _, units, loads = read_inputs()
    output_rows = read_output()
    expected_header = [
        "hour",
        "load_MW",
        "pier_1_MW",
        "ridge_2_MW",
        "cove_3_MW",
        "airport_4_MW",
        "total_generation_MW",
        "hourly_fuel_liters",
        "cumulative_fuel_liters",
    ]

    assert len(output_rows) == len(loads)
    assert list(output_rows[0].keys()) == expected_header

    expected_hours = [row["hour"] for row in loads]
    observed_hours = [int(output_row["hour"]) for output_row in output_rows]
    assert observed_hours == expected_hours

    expected_unit_columns = [f"{unit['unit_id']}_MW" for unit in units]
    assert expected_unit_columns == expected_header[2:2 + len(units)]


def test_hourly_feasibility_and_running_fuel():
    requirements, units, loads = read_inputs()
    output_rows = read_output()
    load_map = {row["hour"]: row["load_MW"] for row in loads}
    cumulative = 0.0

    for output_row in output_rows:
        hour = int(output_row["hour"])
        assert abs(to_float(output_row, "load_MW") - load_map[hour]) <= 1e-6

        generation_sum = 0.0
        hourly_fuel = 0.0
        for unit in units:
            key = f"{unit['unit_id']}_MW"
            output = to_float(output_row, key)
            generation_sum += output
            hourly_fuel += output * unit["fuel_burn_liters_per_MWh"]
            assert unit["min_output_MW"] - 1e-5 <= output <= unit["max_output_MW"] + 1e-5

        assert abs(generation_sum - to_float(output_row, "total_generation_MW")) <= 1e-5
        assert abs(generation_sum - to_float(output_row, "load_MW")) <= 1e-5
        assert abs(hourly_fuel - to_float(output_row, "hourly_fuel_liters")) <= 1e-4

        cumulative += hourly_fuel
        assert abs(cumulative - to_float(output_row, "cumulative_fuel_liters")) <= 1e-4

    assert cumulative <= float(requirements["daily_fuel_budget_liters"]) + 1e-4


def test_total_cost_is_optimal():
    requirements, units, loads = read_inputs()
    output_rows = read_output()
    reference = optimal_reference(requirements, units, loads)
    observed_cost = total_reported_cost(output_rows, units)

    assert abs(observed_cost - reference["total_cost"]) <= 1e-2
    assert abs(to_float(output_rows[-1], "cumulative_fuel_liters") - reference["total_fuel"]) <= 1e-2


if __name__ == "__main__":
    test_schema_and_row_count()
    test_hourly_feasibility_and_running_fuel()
    test_total_cost_is_optimal()
