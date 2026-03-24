#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/root/data}"
OUTPUT_DIR="${OUTPUT_DIR:-/root/output}"

python3 <<'PY'
import csv
import json
import os

data_dir = os.environ.get("DATA_DIR", "/root/data")
output_dir = os.environ.get("OUTPUT_DIR", "/root/output")

roster_path = os.path.join(data_dir, "reservoir_roster.txt")
thresholds_path = os.path.join(data_dir, "spillway_thresholds.csv")
levels_path = os.path.join(data_dir, "reservoir_hourly_levels.json")
output_path = os.path.join(output_dir, "spillway_alerts.json")

start_date = "2025-10-03"
end_date = "2025-10-07"

with open(roster_path, "r", encoding="utf-8") as handle:
    roster = [line.strip() for line in handle if line.strip()]

with open(thresholds_path, "r", encoding="utf-8") as handle:
    thresholds = {
        row["reservoir_id"]: {
            "reservoir_name": row["reservoir_name"],
            "action_stage_ft": float(row["action_stage_ft"]),
            "flood_stage_ft": float(row["flood_stage_ft"]),
            "major_stage_ft": float(row["major_stage_ft"]),
        }
        for row in csv.DictReader(handle)
    }

with open(levels_path, "r", encoding="utf-8") as handle:
    records = json.load(handle)

daily_peaks = {reservoir_id: {} for reservoir_id in roster if reservoir_id in thresholds}

for record in records:
    reservoir_id = record["reservoir_id"]
    date = record["date"]
    if reservoir_id not in daily_peaks or not (start_date <= date <= end_date):
        continue
    daily_peaks[reservoir_id][date] = max(record["hourly_levels_ft"])

def classify(level, config):
    if level >= config["major_stage_ft"]:
        return "major"
    if level >= config["flood_stage_ft"]:
        return "flood"
    if level >= config["action_stage_ft"]:
        return "action"
    return "normal"

severity_rank = {"normal": 0, "action": 1, "flood": 2, "major": 3}

alerts = []
for reservoir_id, peaks_by_day in daily_peaks.items():
    config = thresholds[reservoir_id]
    flood_days = sum(
        1 for peak in peaks_by_day.values() if peak >= config["flood_stage_ft"]
    )
    if flood_days == 0:
        continue

    peak_level = max(peaks_by_day.values())
    peak_day = min(date for date, peak in peaks_by_day.items() if peak == peak_level)
    highest_severity = "normal"
    for peak in peaks_by_day.values():
        severity = classify(peak, config)
        if severity_rank[severity] > severity_rank[highest_severity]:
            highest_severity = severity

    alerts.append(
        {
            "reservoir_id": reservoir_id,
            "reservoir_name": config["reservoir_name"],
            "flood_risk_days": flood_days,
            "highest_severity": highest_severity,
            "peak_day": peak_day,
            "peak_level_ft": peak_level,
        }
    )

alerts.sort(
    key=lambda item: (
        -item["flood_risk_days"],
        -item["peak_level_ft"],
        item["reservoir_id"],
    )
)

payload = {
    "report_window": {
        "start_date": start_date,
        "end_date": end_date,
    },
    "summary": {
        "reservoirs_evaluated": len(daily_peaks),
        "reservoirs_with_flood_stage": len(alerts),
    },
    "reservoir_alerts": alerts,
}

os.makedirs(output_dir, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
