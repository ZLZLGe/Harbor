#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/root/data}"
OUTPUT_PATH="${OUTPUT_PATH:-/root/output/river_access_advisories.json}"

python3 <<'PY'
import csv
import json
import os


data_dir = os.environ.get("DATA_DIR", "/root/data")
output_path = os.environ.get("OUTPUT_PATH", "/root/output/river_access_advisories.json")

parks_path = os.path.join(data_dir, "park_gage_assignments.json")
observations_path = os.path.join(data_dir, "latest_stage_snapshot.csv")
thresholds_path = os.path.join(data_dir, "gauge_threshold_export.csv")

with open(parks_path, "r", encoding="utf-8") as handle:
    parks_payload = json.load(handle)

snapshot_time = parks_payload["snapshot_time"]
parks = parks_payload["parks"]

observations = {}
with open(observations_path, "r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        observations[row["station_id"].strip()] = float(row["observed_stage_ft"])

with open(thresholds_path, "r", encoding="utf-8", newline="") as handle:
    reader = csv.reader(handle)
    headers = next(reader)
    rows = [row[: len(headers)] for row in reader if row]

thresholds = {}
for row in rows:
    record = dict(zip(headers, row))
    station_id = record["usgs id"].strip()
    raw_flood_stage = record["flood stage"].strip()
    if not station_id or not raw_flood_stage or raw_flood_stage == "-9999":
        continue
    thresholds[station_id] = float(raw_flood_stage)

advisories = []
for park in parks:
    park_id = park["park_id"]
    station_id = park["station_id"].strip()
    if station_id not in thresholds or station_id not in observations:
        continue

    flood_stage = thresholds[station_id]
    observed_stage = observations[station_id]
    if observed_stage < flood_stage:
        continue

    advisories.append(
        {
            "park_id": park_id,
            "station_id": station_id,
            "flood_stage_ft": round(flood_stage, 1),
            "observed_stage_ft": round(observed_stage, 1),
            "exceedance_ft": round(observed_stage - flood_stage, 1),
        }
    )

advisories.sort(key=lambda item: (-item["exceedance_ft"], item["park_id"]))

result = {
    "snapshot_time": snapshot_time,
    "advisory_count": len(advisories),
    "advisories": advisories,
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
PY
