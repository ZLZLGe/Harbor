#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
OUTPUT_PATH="${OUTPUT_PATH:-$ROOT_DIR/procurement_frontier.csv}"
export DATA_DIR OUTPUT_PATH

cd "$ROOT_DIR"

python3 - <<'PY'
import os
from pathlib import Path

import pandas as pd


def is_dominated(row, others):
    for other in others:
        if other["bundle_id"] == row["bundle_id"]:
            continue
        if (
            other["expected_annual_coverage_km"] >= row["expected_annual_coverage_km"]
            and other["total_3yr_cost_usd"] <= row["total_3yr_cost_usd"]
            and (
                other["expected_annual_coverage_km"] > row["expected_annual_coverage_km"]
                or other["total_3yr_cost_usd"] < row["total_3yr_cost_usd"]
            )
        ):
            return True
    return False

data_dir = Path(os.environ["DATA_DIR"])
output_path = Path(os.environ["OUTPUT_PATH"])
components = pd.read_csv(data_dir / "bundle_components.csv")
operations = pd.read_csv(data_dir / "bundle_operations.csv")

components["line_cost_usd"] = components["quantity"] * components["unit_cost_usd"]
capex = (
    components.groupby(["bundle_id", "vendor", "buoy_model", "sensor_suite"], as_index=False)["line_cost_usd"]
    .sum()
    .rename(columns={"line_cost_usd": "procurement_capex_usd"})
)

bundles = capex.merge(operations, on="bundle_id", how="inner", validate="one_to_one")
bundles["expected_annual_coverage_km"] = (
    bundles["shoreline_km"] * bundles["uptime_rate"] * bundles["data_return_rate"]
)
bundles = bundles[bundles["expected_annual_coverage_km"] >= 170].copy()
bundles["total_3yr_cost_usd"] = (
    bundles["procurement_capex_usd"]
    + 3 * (bundles["annual_support_usd"] + bundles["annual_permit_usd"])
    + bundles["replacement_events_3yr"] * bundles["replacement_cost_usd"]
)

records = bundles.to_dict("records")
frontier = bundles[[not is_dominated(row, records) for row in records]].copy()
frontier = frontier[
    [
        "expected_annual_coverage_km",
        "total_3yr_cost_usd",
        "bundle_id",
        "vendor",
        "buoy_model",
        "sensor_suite",
    ]
]

frontier["expected_annual_coverage_km"] = frontier["expected_annual_coverage_km"].round(2)
frontier["total_3yr_cost_usd"] = frontier["total_3yr_cost_usd"].round(2)
frontier = frontier.sort_values(
    by=[
        "expected_annual_coverage_km",
        "total_3yr_cost_usd",
        "bundle_id",
        "vendor",
        "buoy_model",
        "sensor_suite",
    ],
    ascending=[False, True, True, True, True, True],
).reset_index(drop=True)

frontier.to_csv(output_path, index=False)
PY
