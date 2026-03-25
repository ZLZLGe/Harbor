#!/bin/bash

set -euo pipefail

LOG_FILE="${LOG_FILE:-/root/data/turbine_sensor_logs.csv}"
LABEL_FILE="${LABEL_FILE:-/root/data/maintenance_labels.csv}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/results/turbine_features.csv}"
export LOG_FILE LABEL_FILE OUTPUT_FILE

mkdir -p "$(dirname "$OUTPUT_FILE")"

python3 - <<'PY'
import csv
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta


LOG_FILE = os.environ.get("LOG_FILE", "/root/data/turbine_sensor_logs.csv")
LABEL_FILE = os.environ.get("LABEL_FILE", "/root/data/maintenance_labels.csv")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/results/turbine_features.csv")
TS_FORMAT = "%Y-%m-%dT%H:%M"
HEADER = [
    "turbine_id",
    "snapshot_ts",
    "split",
    "failure_within_24h",
    "rpm_mean_60m",
    "rpm_std_60m",
    "temp_mean_180m",
    "temp_slope_180m",
    "vibration_std_60m",
    "pressure_missing_rate_180m",
    "alarm_count_180m",
]


def parse_ts(value):
    return datetime.strptime(value, TS_FORMAT)


def parse_float(value):
    return None if value == "" else float(value)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def pop_std(values):
    if not values:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / len(values))


def slope(points):
    if len(points) < 2:
        return 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_bar = mean(xs)
    y_bar = mean(ys)
    denom = sum((x - x_bar) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    numer = sum((x - x_bar) * (y - y_bar) for x, y in points)
    return numer / denom


logs_by_turbine = defaultdict(dict)
with open(LOG_FILE, newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        ts = parse_ts(row["event_ts"])
        logs_by_turbine[row["turbine_id"]][ts] = {
            "rpm": parse_float(row["rpm"]),
            "temp_c": parse_float(row["temp_c"]),
            "vibration_mm_s": parse_float(row["vibration_mm_s"]),
            "pressure_kpa": parse_float(row["pressure_kpa"]),
            "alarm_flag": int(row["alarm_flag"]),
        }


def build_row(label_row):
    turbine_id = label_row["turbine_id"]
    snapshot_ts = parse_ts(label_row["snapshot_ts"])
    turbine_logs = logs_by_turbine[turbine_id]

    sixty_start = snapshot_ts - timedelta(minutes=59)
    one_eighty_start = snapshot_ts - timedelta(minutes=179)

    sixty_rows = []
    one_eighty_rows = []
    ts = one_eighty_start
    pressure_missing = 0
    while ts <= snapshot_ts:
        record = turbine_logs.get(ts)
        if record is None or record["pressure_kpa"] is None:
            pressure_missing += 1
        if record is not None:
            one_eighty_rows.append((ts, record))
            if ts >= sixty_start:
                sixty_rows.append((ts, record))
        ts += timedelta(minutes=1)

    rpm_values = [record["rpm"] for _, record in sixty_rows if record["rpm"] is not None]
    temp_values = [record["temp_c"] for _, record in one_eighty_rows if record["temp_c"] is not None]
    temp_points = [
        (int((ts - one_eighty_start).total_seconds() // 60), record["temp_c"])
        for ts, record in one_eighty_rows
        if record["temp_c"] is not None
    ]
    vibration_values = [
        record["vibration_mm_s"]
        for _, record in sixty_rows
        if record["vibration_mm_s"] is not None
    ]
    alarm_count = sum(record["alarm_flag"] for _, record in one_eighty_rows)

    return {
        "turbine_id": turbine_id,
        "snapshot_ts": label_row["snapshot_ts"],
        "split": label_row["split"],
        "failure_within_24h": str(int(label_row["failure_within_24h"])),
        "rpm_mean_60m": f"{mean(rpm_values):.10f}",
        "rpm_std_60m": f"{pop_std(rpm_values):.10f}",
        "temp_mean_180m": f"{mean(temp_values):.10f}",
        "temp_slope_180m": f"{slope(temp_points):.10f}",
        "vibration_std_60m": f"{pop_std(vibration_values):.10f}",
        "pressure_missing_rate_180m": f"{pressure_missing / 180.0:.10f}",
        "alarm_count_180m": str(alarm_count),
    }


with open(LABEL_FILE, newline="", encoding="utf-8") as handle:
    label_rows = list(csv.DictReader(handle))

output_rows = [build_row(row) for row in label_rows]
output_rows.sort(key=lambda row: (row["turbine_id"], row["snapshot_ts"]))

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=HEADER)
    writer.writeheader()
    writer.writerows(output_rows)
PY
