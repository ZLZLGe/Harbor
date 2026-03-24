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

start_date = pd.Timestamp("2025-03-18")
end_date = pd.Timestamp("2025-03-22 23:59:59")

with open(data_dir / "wisconsin_gauges.txt", "r", encoding="utf-8") as handle:
    gauge_ids = [line.strip() for line in handle if line.strip()]

thresholds = pd.read_csv(
    data_dir / "wisconsin_flood_thresholds.csv",
    dtype={"station_id": str},
)
observations = pd.read_csv(
    data_dir / "wisconsin_stage_observations.csv",
    dtype={"station_id": str},
    parse_dates=["observed_at"],
)

threshold_map = thresholds.set_index("station_id")["flood_stage_ft"].to_dict()

observations = observations[observations["station_id"].isin(gauge_ids)].copy()
observations = observations[
    (observations["observed_at"] >= start_date)
    & (observations["observed_at"] <= end_date)
].copy()
observations["day"] = observations["observed_at"].dt.strftime("%Y-%m-%d")

daily_max = (
    observations.groupby(["station_id", "day"], as_index=False)["stage_ft"]
    .max()
    .sort_values(["station_id", "day"])
)

results = []
for station_id in gauge_ids:
    station_daily = daily_max[daily_max["station_id"] == station_id]
    if station_daily.empty:
        continue

    flood_stage = threshold_map[station_id]
    flood_rows = station_daily[station_daily["stage_ft"] >= flood_stage]
    if flood_rows.empty:
        continue

    results.append(
        {
            "station_id": station_id,
            "flood_days": int(len(flood_rows)),
            "flood_dates": flood_rows["day"].tolist(),
        }
    )

results.sort(key=lambda item: (-item["flood_days"], item["station_id"]))

output_dir.mkdir(parents=True, exist_ok=True)
with open(output_dir / "river_watch_summary.json", "w", encoding="utf-8") as handle:
    json.dump(results, handle, indent=2)
PYTHON
