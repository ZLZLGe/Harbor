#!/bin/bash
set -euo pipefail

export DATA_DIR="${DATA_DIR:-/root/data}"
export OUTPUT_DIR="${OUTPUT_DIR:-/root/output}"

python3 <<'PYTHON'
import json
import os
from pathlib import Path

import pandas as pd

data_dir = Path(os.environ["DATA_DIR"])
output_dir = Path(os.environ["OUTPUT_DIR"])

window_start = pd.Timestamp("2025-09-10")
window_end = pd.Timestamp("2025-09-14 23:59:59")

with open(data_dir / "underpass_thresholds.json", "r", encoding="utf-8") as handle:
    thresholds_payload = json.load(handle)

thresholds = pd.DataFrame(thresholds_payload["underpasses"])
observations = pd.read_csv(
    data_dir / "underpass_depth_readings.csv",
    dtype={"underpass_id": str},
    parse_dates=["observed_at"],
)

observations = observations[
    observations["underpass_id"].isin(thresholds["underpass_id"])
].copy()
observations = observations[
    (observations["observed_at"] >= window_start)
    & (observations["observed_at"] <= window_end)
].copy()

observations["day"] = observations["observed_at"].dt.strftime("%Y-%m-%d")

daily_max = (
    observations.groupby(["underpass_id", "day"], as_index=False)["depth_cm"]
    .max()
    .sort_values(["underpass_id", "day"])
)

joined = daily_max.merge(thresholds, on="underpass_id", how="inner")
blocked = joined[joined["depth_cm"] >= joined["traffic_control_depth_cm"]].copy()

blocked["worst_closure_category"] = "traffic_control"
blocked.loc[
    blocked["depth_cm"] >= blocked["full_closure_depth_cm"],
    "worst_closure_category",
] = "full_closure"

summary = (
    blocked.groupby("underpass_id", as_index=False)
    .agg(
        blocked_days=("day", "nunique"),
        saw_full_closure=(
            "worst_closure_category",
            lambda values: "full_closure" in set(values),
        ),
    )
)

summary["worst_closure_category"] = summary["saw_full_closure"].map(
    {True: "full_closure", False: "traffic_control"}
)
summary = summary[["underpass_id", "blocked_days", "worst_closure_category"]]
summary = summary.sort_values(
    ["blocked_days", "underpass_id"],
    ascending=[False, True],
).reset_index(drop=True)

output_dir.mkdir(parents=True, exist_ok=True)
summary.to_csv(output_dir / "underpass_closure_days.csv", index=False)
PYTHON
