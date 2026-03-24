#!/bin/bash
set -euo pipefail

python3 <<'PYTHON'
import csv
import os
import re


ROSTER_PATH = "/root/data/station_roster_mixed.txt"
THRESHOLD_PATH = "/root/data/nws_thresholds_batch.csv"
OUTPUT_PATH = "/root/output/station_threshold_catalog.csv"


def normalize_station_id(text):
    candidates = re.findall(r"\d{7,8}", text)
    if not candidates:
        return None
    return candidates[-1].zfill(8)


roster_station_ids = set()
with open(ROSTER_PATH, "r", encoding="utf-8") as handle:
    for line in handle:
        station_id = normalize_station_id(line)
        if station_id:
            roster_station_ids.add(station_id)


with open(THRESHOLD_PATH, "r", encoding="utf-8", newline="") as handle:
    reader = csv.reader(handle)
    headers = next(reader)
    rows = [row[: len(headers)] for row in reader if row]


def parse_stage(raw_value):
    value = raw_value.strip()
    if not value or value == "-9999":
        return None
    return float(value)


matched_rows = []
for row in rows:
    record = dict(zip(headers, row))
    station_id = record["usgs id"].strip()
    if not station_id or station_id not in roster_station_ids:
        continue

    action_stage = parse_stage(record["action stage"])
    flood_stage = parse_stage(record["flood stage"])
    moderate_stage = parse_stage(record["moderate flood stage"])
    major_stage = parse_stage(record["major flood stage"])

    if None in (action_stage, flood_stage, moderate_stage, major_stage):
        continue

    matched_rows.append(
        {
            "station_id": station_id,
            "location_name": record["location name"].strip(),
            "state": record["state"].strip(),
            "action_stage": f"{action_stage:.1f}",
            "flood_stage": f"{flood_stage:.1f}",
            "moderate_stage": f"{moderate_stage:.1f}",
            "major_stage": f"{major_stage:.1f}",
        }
    )

matched_rows.sort(key=lambda item: (item["state"], item["station_id"]))

os.makedirs("/root/output", exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "station_id",
            "location_name",
            "state",
            "action_stage",
            "flood_stage",
            "moderate_stage",
            "major_stage",
        ],
    )
    writer.writeheader()
    writer.writerows(matched_rows)
PYTHON
