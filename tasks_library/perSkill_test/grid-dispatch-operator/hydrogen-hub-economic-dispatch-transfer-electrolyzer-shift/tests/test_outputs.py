import csv
import os
from pathlib import Path

import pytest
import yaml


SHIFT_FILE = Path("/root/shift_requirements.yaml")
FLEET_FILE = Path("/root/electrolyzer_fleet.csv")
OUTPUT_FILE = Path("/root/electrolyzer_shift.md")
EPS = 1e-6


def read_inputs():
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

    return shift, stacks


def parse_markdown_table(lines, heading):
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise AssertionError(f"Missing section heading: {heading}") from exc

    table_lines = []
    for line in lines[start + 1 :]:
        if not line.strip():
            if table_lines:
                break
            continue
        if line.lstrip().startswith("|"):
            table_lines.append(line.strip())
            continue
        if table_lines:
            break

    assert len(table_lines) >= 2, f"Section {heading} is missing a Markdown table"
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for raw_line in table_lines[2:]:
        cells = [cell.strip() for cell in raw_line.strip("|").split("|")]
        assert len(cells) == len(headers), f"Malformed table row in {heading}: {raw_line}"
        rows.append(dict(zip(headers, cells)))
    return rows


def read_output():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    content = OUTPUT_FILE.read_text(encoding="utf-8").strip()
    lines = content.splitlines()
    assert lines[0].strip() == "# Hydrogen Hub Shift Dispatch"

    summary_rows = parse_markdown_table(lines, "## Shift Summary")
    stack_rows = parse_markdown_table(lines, "## Stack Dispatch")
    total_rows = parse_markdown_table(lines, "## Totals")

    summary = {row["field"]: row["value"] for row in summary_rows}
    totals = {row["metric"]: row["value"] for row in total_rows}

    return {
        "summary": summary,
        "stack_rows": stack_rows,
        "totals": totals,
    }


def to_float(value):
    return float(value)


def reference_solution(shift, stacks):
    shift_hours = float(shift["shift_hours"])
    power_price = float(shift["power_price_dollars_per_MWh"])
    target_hydrogen = float(shift["hydrogen_target_kg"])
    site_power_cap = float(shift["site_power_cap_MW"])
    required_idle_flexibility = float(shift["required_idle_flexibility_MW"])

    dispatch_limit = min(
        site_power_cap,
        sum(stack["max_load_MW"] for stack in stacks) - required_idle_flexibility,
    )

    scheduled = {stack["stack_id"]: stack["min_load_MW"] for stack in stacks}
    base_load = sum(scheduled.values())
    assert base_load <= dispatch_limit + EPS

    def hydrogen_per_mw(stack):
        return shift_hours * stack["hydrogen_yield_kg_per_MWh"]

    total_hydrogen = sum(
        scheduled[stack["stack_id"]] * hydrogen_per_mw(stack)
        for stack in stacks
    )
    remaining_hydrogen = max(0.0, target_hydrogen - total_hydrogen)
    remaining_dispatch_room = dispatch_limit - base_load

    ordered = sorted(
        stacks,
        key=lambda stack: (
            (power_price + stack["stack_wear_dollars_per_MWh"]) / stack["hydrogen_yield_kg_per_MWh"],
            power_price + stack["stack_wear_dollars_per_MWh"],
            stack["stack_id"],
        ),
    )

    for stack in ordered:
        if remaining_hydrogen <= EPS:
            break
        headroom = stack["max_load_MW"] - scheduled[stack["stack_id"]]
        if headroom <= EPS or remaining_dispatch_room <= EPS:
            continue
        need = remaining_hydrogen / hydrogen_per_mw(stack)
        add_load = min(headroom, remaining_dispatch_room, need)
        scheduled[stack["stack_id"]] += add_load
        remaining_hydrogen -= add_load * hydrogen_per_mw(stack)
        remaining_dispatch_room -= add_load

    assert remaining_hydrogen <= 1e-6

    total_cost = 0.0
    total_power = 0.0
    reserved_flexibility = 0.0
    achieved_hydrogen = 0.0

    for stack in stacks:
        load = scheduled[stack["stack_id"]]
        total_power += load
        achieved_hydrogen += load * hydrogen_per_mw(stack)
        total_cost += load * shift_hours * (power_price + stack["stack_wear_dollars_per_MWh"])
        reserved_flexibility += stack["max_load_MW"] - load

    return {
        "scheduled": scheduled,
        "total_power": total_power,
        "achieved_hydrogen": achieved_hydrogen,
        "total_cost": total_cost,
        "reserved_flexibility": reserved_flexibility,
    }


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def report():
    return read_output()


@pytest.fixture(scope="module")
def reference(inputs):
    shift, stacks = inputs
    return reference_solution(shift, stacks)


def test_schema_and_summary(inputs, report):
    shift, stacks = inputs
    summary = report["summary"]

    assert summary["hub_name"] == shift["hub_name"]
    assert summary["shift_label"] == shift["shift_label"]
    assert summary["shift_start"] == shift["shift_start"]
    assert to_float(summary["shift_hours"]) == pytest.approx(float(shift["shift_hours"]), abs=1e-6)
    assert to_float(summary["hydrogen_target_kg"]) == pytest.approx(float(shift["hydrogen_target_kg"]), abs=1e-6)
    assert to_float(summary["site_power_cap_MW"]) == pytest.approx(float(shift["site_power_cap_MW"]), abs=1e-6)
    assert to_float(summary["required_idle_flexibility_MW"]) == pytest.approx(
        float(shift["required_idle_flexibility_MW"]),
        abs=1e-6,
    )

    expected_columns = {
        "stack_id",
        "technology",
        "scheduled_load_MW",
        "hydrogen_kg",
        "stack_cost_dollars",
        "idle_headroom_MW",
    }
    assert len(report["stack_rows"]) == len(stacks)
    for row in report["stack_rows"]:
        assert set(row.keys()) == expected_columns

    expected_totals = {
        "total_power_MW",
        "achieved_hydrogen_kg",
        "total_operating_cost_dollars",
        "reserved_flexibility_MW",
    }
    assert set(report["totals"].keys()) == expected_totals


def test_stack_order_and_accounting(inputs, report):
    shift, stacks = inputs
    stack_rows = report["stack_rows"]
    shift_hours = float(shift["shift_hours"])
    power_price = float(shift["power_price_dollars_per_MWh"])

    expected_ids = [stack["stack_id"] for stack in stacks]
    observed_ids = [row["stack_id"] for row in stack_rows]
    assert observed_ids == expected_ids

    total_power = 0.0
    total_hydrogen = 0.0
    total_cost = 0.0
    total_headroom = 0.0

    for stack, row in zip(stacks, stack_rows):
        load = to_float(row["scheduled_load_MW"])
        hydrogen = to_float(row["hydrogen_kg"])
        cost = to_float(row["stack_cost_dollars"])
        headroom = to_float(row["idle_headroom_MW"])

        assert row["technology"] == stack["technology"]
        assert stack["min_load_MW"] - EPS <= load <= stack["max_load_MW"] + EPS

        expected_hydrogen = load * shift_hours * stack["hydrogen_yield_kg_per_MWh"]
        expected_cost = load * shift_hours * (power_price + stack["stack_wear_dollars_per_MWh"])
        expected_headroom = stack["max_load_MW"] - load

        assert hydrogen == pytest.approx(expected_hydrogen, abs=1e-6)
        assert cost == pytest.approx(expected_cost, abs=1e-6)
        assert headroom == pytest.approx(expected_headroom, abs=1e-6)

        total_power += load
        total_hydrogen += hydrogen
        total_cost += cost
        total_headroom += headroom

    totals = report["totals"]
    assert to_float(totals["total_power_MW"]) == pytest.approx(total_power, abs=1e-6)
    assert to_float(totals["achieved_hydrogen_kg"]) == pytest.approx(total_hydrogen, abs=1e-6)
    assert to_float(totals["total_operating_cost_dollars"]) == pytest.approx(total_cost, abs=1e-6)
    assert to_float(totals["reserved_flexibility_MW"]) == pytest.approx(total_headroom, abs=1e-6)


def test_feasibility(inputs, report):
    shift, stacks = inputs
    totals = report["totals"]

    total_power = to_float(totals["total_power_MW"])
    achieved_hydrogen = to_float(totals["achieved_hydrogen_kg"])
    reserved_flexibility = to_float(totals["reserved_flexibility_MW"])

    assert total_power <= float(shift["site_power_cap_MW"]) + EPS
    assert reserved_flexibility >= float(shift["required_idle_flexibility_MW"]) - EPS
    assert achieved_hydrogen >= float(shift["hydrogen_target_kg"]) - EPS

    derived_headroom = sum(
        stack["max_load_MW"] - to_float(row["scheduled_load_MW"])
        for stack, row in zip(stacks, report["stack_rows"])
    )
    assert reserved_flexibility == pytest.approx(derived_headroom, abs=1e-6)


def test_total_operating_cost_is_optimal(report, reference):
    assert to_float(report["totals"]["total_operating_cost_dollars"]) == pytest.approx(
        reference["total_cost"],
        abs=1e-6,
    )
    assert to_float(report["totals"]["total_power_MW"]) == pytest.approx(reference["total_power"], abs=1e-6)
    assert to_float(report["totals"]["achieved_hydrogen_kg"]) == pytest.approx(
        reference["achieved_hydrogen"],
        abs=1e-6,
    )
    assert to_float(report["totals"]["reserved_flexibility_MW"]) == pytest.approx(
        reference["reserved_flexibility"],
        abs=1e-6,
    )
