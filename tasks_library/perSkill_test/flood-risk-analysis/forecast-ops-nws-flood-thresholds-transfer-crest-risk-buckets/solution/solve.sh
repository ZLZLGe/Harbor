#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/root/data}"
OUTPUT_PATH="${OUTPUT_PATH:-/root/output/forecast_crest_risk.json}"

python3 <<'PY'
import csv
import json
import os
from datetime import datetime, timedelta


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


data_dir = os.environ.get("DATA_DIR", "/root/data")
output_path = os.environ.get("OUTPUT_PATH", "/root/output/forecast_crest_risk.json")

watchlist_path = os.path.join(data_dir, "station_watchlist.csv")
forecast_path = os.path.join(data_dir, "forecast_crest_guidance.json")
threshold_path = os.path.join(data_dir, "gauge_threshold_export.csv")

with open(watchlist_path, "r", encoding="utf-8", newline="") as handle:
    watchlist_reader = csv.DictReader(handle)
    watchlist_ids = {row["station_id"].strip() for row in watchlist_reader}

with open(threshold_path, "r", encoding="utf-8", newline="") as handle:
    reader = csv.reader(handle)
    headers = next(reader)
    rows = [row[: len(headers)] for row in reader]

thresholds = {}
for row in rows:
    record = dict(zip(headers, row))
    station_id = record["usgs id"].strip()
    if station_id not in watchlist_ids:
        continue
    thresholds[station_id] = {
        "location_name": record["location name"].strip(),
        "action": float(record["action stage"]),
        "minor": float(record["flood stage"]),
        "moderate": float(record["moderate flood stage"]),
        "major": float(record["major flood stage"]),
    }

with open(forecast_path, "r", encoding="utf-8") as handle:
    forecast_payload = json.load(handle)

issued_at = forecast_payload["issued_at"]
issued_dt = parse_time(issued_at)
window_end_dt = issued_dt + timedelta(hours=48)
window_end = window_end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

buckets = {
    "no_risk": [],
    "action": [],
    "minor": [],
    "moderate": [],
    "major": [],
}

for station in forecast_payload["stations"]:
    station_id = station["station_id"].strip()
    if station_id not in thresholds:
        continue

    candidates = []
    for point in station["forecast_points"]:
        valid_time = parse_time(point["valid_time"])
        if issued_dt <= valid_time <= window_end_dt:
            candidates.append(point)

    if not candidates:
        continue

    crest_point = max(candidates, key=lambda point: (point["stage_ft"], point["valid_time"]))
    crest_stage = round(float(crest_point["stage_ft"]), 1)
    station_thresholds = thresholds[station_id]

    if crest_stage < station_thresholds["action"]:
        bucket_name = "no_risk"
        reference_threshold = "action"
    elif crest_stage < station_thresholds["minor"]:
        bucket_name = "action"
        reference_threshold = "action"
    elif crest_stage < station_thresholds["moderate"]:
        bucket_name = "minor"
        reference_threshold = "minor"
    elif crest_stage < station_thresholds["major"]:
        bucket_name = "moderate"
        reference_threshold = "moderate"
    else:
        bucket_name = "major"
        reference_threshold = "major"

    threshold_ft = round(station_thresholds[reference_threshold], 1)
    buckets[bucket_name].append(
        {
            "station_id": station_id,
            "location_name": station_thresholds["location_name"],
            "crest_valid_time": crest_point["valid_time"],
            "forecast_crest_ft": crest_stage,
            "reference_threshold": reference_threshold,
            "threshold_ft": threshold_ft,
            "margin_ft": round(crest_stage - threshold_ft, 1),
        }
    )

for bucket_entries in buckets.values():
    bucket_entries.sort(key=lambda item: item["station_id"])

result = {
    "issued_at": issued_at,
    "window_end": window_end,
    "buckets": buckets,
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
PY
