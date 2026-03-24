#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import os
from pathlib import Path


def resolve_existing_path(*candidates):
    for candidate in candidates:
        path = Path(candidate)
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    raise FileNotFoundError(f"None of these paths exist: {candidates}")


UNITS_PATH = resolve_existing_path("/root/thermal_units.csv", "environment/thermal_units.csv")
BLOCKS_PATH = resolve_existing_path("/root/load_blocks.csv", "environment/load_blocks.csv")
CONFIG_PATH = resolve_existing_path("/root/study_config.json", "environment/study_config.json")
OUTPUT_PATH = Path("/root/breakpoint_study.json")
if not OUTPUT_PATH.parent.exists() or not os.access(OUTPUT_PATH.parent, os.W_OK):
    OUTPUT_PATH = Path("breakpoint_study.json")


def round2(value):
    return round(float(value), 2)


def read_units(path):
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    units = []
    for row in rows:
        units.append(
            {
                "unit_id": row["unit_id"],
                "pmin_mw": float(row["pmin_mw"]),
                "pmax_mw": float(row["pmax_mw"]),
                "cost_quadratic": float(row["cost_quadratic"]),
                "cost_linear": float(row["cost_linear"]),
                "cost_fixed": float(row["cost_fixed"]),
            }
        )
    return units


def read_blocks(path):
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [
        {"block_id": row["block_id"], "load_mw": float(row["load_mw"])}
        for row in rows
    ]


def generator_output(unit, lambda_value):
    unconstrained = (
        lambda_value - unit["cost_linear"]
    ) / (2.0 * unit["cost_quadratic"])
    return max(unit["pmin_mw"], min(unit["pmax_mw"], unconstrained))


def solve_dispatch(units, load_mw):
    min_feasible = sum(unit["pmin_mw"] for unit in units)
    max_feasible = sum(unit["pmax_mw"] for unit in units)
    if load_mw < min_feasible - 1e-9 or load_mw > max_feasible + 1e-9:
        raise ValueError(f"Load {load_mw} MW is infeasible")

    low = min(
        2.0 * unit["cost_quadratic"] * unit["pmin_mw"] + unit["cost_linear"]
        for unit in units
    ) - 100.0
    high = max(
        2.0 * unit["cost_quadratic"] * unit["pmax_mw"] + unit["cost_linear"]
        for unit in units
    ) + 100.0

    for _ in range(250):
        midpoint = (low + high) / 2.0
        total_output = sum(generator_output(unit, midpoint) for unit in units)
        if total_output < load_mw:
            low = midpoint
        else:
            high = midpoint

    lambda_value = (low + high) / 2.0
    outputs = [generator_output(unit, lambda_value) for unit in units]
    total_cost = sum(
        unit["cost_quadratic"] * output * output
        + unit["cost_linear"] * output
        + unit["cost_fixed"]
        for unit, output in zip(units, outputs)
    )

    return {"outputs": outputs, "total_cost": total_cost}


def main():
    units = read_units(UNITS_PATH)
    blocks = read_blocks(BLOCKS_PATH)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    report = {"load_blocks": []}
    breakpoint = None

    for block in blocks:
        solved = solve_dispatch(units, block["load_mw"])
        one_mw_up = solve_dispatch(units, block["load_mw"] + 1.0)
        marginal_cost = one_mw_up["total_cost"] - solved["total_cost"]

        dispatch = []
        standby_output = None
        for unit, output in zip(units, solved["outputs"]):
            dispatch.append(
                {
                    "unit_id": unit["unit_id"],
                    "output_mw": round2(output),
                }
            )
            if unit["unit_id"] == config["standby_unit_id"]:
                standby_output = output

        report["load_blocks"].append(
            {
                "block_id": block["block_id"],
                "load_mw": round2(block["load_mw"]),
                "total_cost_dollars_per_hour": round2(solved["total_cost"]),
                "marginal_system_cost_dollars_per_mwh": round2(marginal_cost),
                "dispatch": dispatch,
            }
        )

        if (
            breakpoint is None
            and standby_output is not None
            and standby_output > config["dispatch_threshold_mw"]
        ):
            breakpoint = {
                "unit_id": config["standby_unit_id"],
                "threshold_mw": round2(config["dispatch_threshold_mw"]),
                "first_block_id": block["block_id"],
                "first_load_mw": round2(block["load_mw"]),
                "dispatch_mw": round2(standby_output),
            }

    if breakpoint is None:
        raise ValueError("No load block exceeded the standby threshold")

    report["standby_breakpoint"] = breakpoint
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
