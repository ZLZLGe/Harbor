#!/bin/bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/root}"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
OUTPUT_PATH="${OUTPUT_PATH:-$ROOT_DIR/battery_policy_frontier.csv}"

cd "$ROOT_DIR"

python3 - <<'PY'
import json
import os
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(os.environ.get("ROOT_DIR", "/root"))
DATA_DIR = Path(os.environ.get("DATA_DIR", str(ROOT_DIR / "data")))
REGISTRY_PATH = DATA_DIR / "policy_registry.csv"
TRIALS_PATH = DATA_DIR / "cycling_trial_summaries.jsonl"
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT_DIR / "battery_policy_frontier.csv")))
REQUIRED_TEMPERATURES = [10, 25, 40]
OUTPUT_COLUMNS = [
    "recovered_capacity_pct",
    "degradation_rate_pct_per_100_cycles",
    "policy_id",
    "charger_family",
    "peak_c_rate",
    "taper_soc",
    "rest_minutes",
]


registry = pd.read_csv(REGISTRY_PATH)

trial_rows = []
with TRIALS_PATH.open() as handle:
    for line in handle:
        row = json.loads(line)
        if row["status"] != "accepted" or int(row["cycles_completed"]) < 180:
            continue
        reference_capacity = float(row["reference_capacity_mah"])
        cycles_completed = float(row["cycles_completed"])
        row["trial_recovered_capacity_pct"] = 100.0 * float(row["recovered_capacity_mah"]) / reference_capacity
        row["trial_degradation_rate_pct_per_100_cycles"] = (
            100.0 * (float(row["capacity_loss_mah"]) / reference_capacity) * (100.0 / cycles_completed)
        )
        trial_rows.append(row)

trials = pd.DataFrame(trial_rows)

temperature_summary = (
    trials.groupby(["policy_id", "temperature_c"], as_index=False)
    .agg(
        trial_count=("replicate_id", "count"),
        recovered_capacity_pct=("trial_recovered_capacity_pct", "mean"),
        degradation_rate_pct_per_100_cycles=("trial_degradation_rate_pct_per_100_cycles", "mean"),
    )
)
temperature_summary = temperature_summary[temperature_summary["trial_count"] >= 2].copy()

policy_metrics = []
for policy_id, group in temperature_summary.groupby("policy_id", sort=False):
    available_temperatures = sorted(group["temperature_c"].tolist())
    if available_temperatures != REQUIRED_TEMPERATURES:
        continue
    policy_metrics.append(
        {
            "policy_id": policy_id,
            "recovered_capacity_pct": float(group["recovered_capacity_pct"].mean()),
            "degradation_rate_pct_per_100_cycles": float(group["degradation_rate_pct_per_100_cycles"].mean()),
        }
    )

policies = pd.DataFrame(policy_metrics)
policies = policies[policies["recovered_capacity_pct"] >= 92.0].copy()

best_by_rounded_pair = {}
for row in policies.to_dict("records"):
    key = (
        round(row["recovered_capacity_pct"], 2),
        round(row["degradation_rate_pct_per_100_cycles"], 2),
    )
    current = best_by_rounded_pair.get(key)
    if current is None or row["policy_id"] < current["policy_id"]:
        best_by_rounded_pair[key] = row

deduped = pd.DataFrame(best_by_rounded_pair.values())

records = deduped.to_dict("records")
frontier_rows = []
for row in records:
    dominated = False
    for other in records:
        if other["policy_id"] == row["policy_id"]:
            continue
        if (
            other["recovered_capacity_pct"] >= row["recovered_capacity_pct"]
            and other["degradation_rate_pct_per_100_cycles"] <= row["degradation_rate_pct_per_100_cycles"]
            and (
                other["recovered_capacity_pct"] > row["recovered_capacity_pct"]
                or other["degradation_rate_pct_per_100_cycles"] < row["degradation_rate_pct_per_100_cycles"]
            )
        ):
            dominated = True
            break
    if not dominated:
        frontier_rows.append(row)

frontier = pd.DataFrame(frontier_rows).merge(registry, on="policy_id", how="inner", validate="one_to_one")
frontier["recovered_capacity_pct"] = frontier["recovered_capacity_pct"].round(2)
frontier["degradation_rate_pct_per_100_cycles"] = frontier["degradation_rate_pct_per_100_cycles"].round(2)
frontier["taper_soc"] = frontier["taper_soc"].astype(int)
frontier["rest_minutes"] = frontier["rest_minutes"].astype(int)
frontier = frontier.sort_values(
    by=[
        "recovered_capacity_pct",
        "degradation_rate_pct_per_100_cycles",
        "policy_id",
        "charger_family",
        "peak_c_rate",
        "taper_soc",
        "rest_minutes",
    ],
    ascending=[False, True, True, True, True, True, True],
).reset_index(drop=True)

frontier[OUTPUT_COLUMNS].to_csv(OUTPUT_PATH, index=False)
PY
