#!/bin/bash
set -euo pipefail

python3 <<'PYTHON'
import csv
import json
import os
from collections import defaultdict
from datetime import date, datetime


DATA_DIR = os.environ.get("DATA_DIR", "/root/data")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/root/output")

ROSTER_PATH = os.path.join(DATA_DIR, "pump_station_roster.txt")
THRESHOLDS_PATH = os.path.join(DATA_DIR, "pump_station_thresholds.tsv")
READINGS_PATH = os.path.join(DATA_DIR, "wet_well_readings.jsonl")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "pump_station_overflow_report.csv")

START_DATE = date.fromisoformat("2025-08-11")
END_DATE = date.fromisoformat("2025-08-15")


with open(ROSTER_PATH, "r", encoding="utf-8") as handle:
    roster = [line.strip() for line in handle if line.strip()]

roster_set = set(roster)

thresholds = {}
with open(THRESHOLDS_PATH, "r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        station_id = row["pump_station_id"]
        if station_id in roster_set:
            thresholds[station_id] = float(row["overflow_level_ft"])

daily_maxima = defaultdict(dict)
with open(READINGS_PATH, "r", encoding="utf-8") as handle:
    for line in handle:
        record = json.loads(line)
        station_id = record["pump_station_id"]
        if station_id not in thresholds:
            continue

        observed_at = datetime.fromisoformat(record["recorded_at"]).date()
        if observed_at < START_DATE or observed_at > END_DATE:
            continue

        level = float(record["wet_well_level_ft"])
        current_max = daily_maxima[station_id].get(observed_at)
        if current_max is None or level > current_max:
            daily_maxima[station_id][observed_at] = level

rows = []
for station_id in roster:
    if station_id not in thresholds:
        continue

    overflow_dates = sorted(
        observed_day.isoformat()
        for observed_day, max_level in daily_maxima.get(station_id, {}).items()
        if max_level >= thresholds[station_id]
    )
    if overflow_dates:
        rows.append(
            {
                "pump_station_id": station_id,
                "overflow_risk_days": str(len(overflow_dates)),
                "first_overflow_date": overflow_dates[0],
            }
        )

rows.sort(
    key=lambda row: (
        row["first_overflow_date"],
        -int(row["overflow_risk_days"]),
        row["pump_station_id"],
    )
)

os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "pump_station_id",
            "overflow_risk_days",
            "first_overflow_date",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PYTHON
