#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/root/data}"
OUTPUT_PATH="${OUTPUT_PATH:-/root/output/wisconsin_flood_window.csv}"

python3 <<'PY'
import csv
import os
from collections import defaultdict

data_dir = os.environ.get("DATA_DIR", "/root/data")
output_path = os.environ.get("OUTPUT_PATH", "/root/output/wisconsin_flood_window.csv")

roster_path = os.path.join(data_dir, "wisconsin_station_roster.txt")
stages_path = os.path.join(data_dir, "wisconsin_stage_observations.csv")
threshold_path = os.path.join(data_dir, "wisconsin_threshold_report.csv")

with open(roster_path, "r", encoding="utf-8") as handle:
    roster = {line.strip() for line in handle if line.strip()}

with open(threshold_path, "r", encoding="utf-8", newline="") as handle:
    reader = csv.reader(handle)
    headers = next(reader)
    threshold_rows = [row[: len(headers)] for row in reader]

thresholds = {}
for row in threshold_rows:
    record = dict(zip(headers, row))
    station_id = record["usgs id"].strip()
    if station_id not in roster:
        continue
    if record["state"].strip() != "WI":
        continue

    raw_value = record["flood stage"].strip()
    if not raw_value or raw_value == "-9999":
        continue

    thresholds[station_id] = float(raw_value)

observations = defaultdict(list)
with open(stages_path, "r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        station_id = row["station_id"].strip()
        if station_id not in thresholds:
            continue
        observations[station_id].append((row["obs_date"], float(row["stage_ft"])))

results = []
for station_id, entries in observations.items():
    entries.sort(key=lambda item: item[0])
    threshold = thresholds[station_id]
    flood_entries = [(obs_date, stage_ft) for obs_date, stage_ft in entries if stage_ft >= threshold]
    if not flood_entries:
        continue

    peak_stage = max(stage_ft for _, stage_ft in entries)
    results.append(
        {
            "station_id": station_id,
            "first_flood_date": flood_entries[0][0],
            "flood_days": len(flood_entries),
            "peak_stage_ft": f"{peak_stage:.1f}",
        }
    )

results.sort(key=lambda item: (item["first_flood_date"], item["station_id"]))

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["station_id", "first_flood_date", "flood_days", "peak_stage_ft"],
    )
    writer.writeheader()
    for row in results:
        writer.writerow(row)
PY
