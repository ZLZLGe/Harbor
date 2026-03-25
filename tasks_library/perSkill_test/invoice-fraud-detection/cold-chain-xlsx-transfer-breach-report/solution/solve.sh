#!/bin/bash
set -euo pipefail

python3 <<'PY'
from datetime import timedelta

import pandas as pd


INPUT_PATH = "/root/cold_chain_monitor_book"
OUTPUT_PATH = "/root/cold_chain_breaches.csv"


def minutes(delta):
    return int(delta.total_seconds() // 60)


def build_intervals(sensor_rows, window_start, window_end, max_gap_minutes):
    intervals = []
    gap_limit = timedelta(minutes=int(max_gap_minutes))

    for idx, row in enumerate(sensor_rows):
        reading_ts = row["reading_ts"]
        next_ts = sensor_rows[idx + 1]["reading_ts"] if idx + 1 < len(sensor_rows) else None
        effective_end = reading_ts + gap_limit if next_ts is None else min(next_ts, reading_ts + gap_limit)

        start = max(reading_ts, window_start)
        end = min(effective_end, window_end)
        if start < end:
            intervals.append((start, end, float(row["temperature_c"])))

    intervals.sort(key=lambda item: item[0])
    return intervals


def uncovered_minutes(intervals, window_start, window_end):
    cursor = window_start
    missing = 0

    for start, end, _temp in intervals:
        if end <= cursor:
            continue
        if start > cursor:
            missing += minutes(start - cursor)
            cursor = start
        if end > cursor:
            cursor = end

    if cursor < window_end:
        missing += minutes(window_end - cursor)

    return missing


def evaluate_batch(batch, trips_by_id, sla_by_route, readings_by_sensor):
    trip = trips_by_id[batch["trip_id"]]
    route_id = trip["route_id"]
    rules = sla_by_route[route_id]

    window_start = batch["load_end_ts"] + timedelta(minutes=int(rules["loading_grace_min"]))
    window_end = batch["handoff_ts"]
    sensor_rows = readings_by_sensor.get(batch["sensor_id"], [])
    intervals = build_intervals(sensor_rows, window_start, window_end, rules["max_gap_min"])

    missing = uncovered_minutes(intervals, window_start, window_end)
    if missing > 0:
        return [
            {
                "batch_id": batch["batch_id"],
                "route_id": route_id,
                "breach_minutes": missing,
                "breach_type": "sensor_missing",
            }
        ]

    limit = float(rules["temp_limit_c"])
    cumulative_minutes = 0
    longest_timeout = 0
    episode_start = None

    for start, end, temperature in intervals:
        duration = minutes(end - start)
        is_over_limit = temperature > limit

        if is_over_limit:
            cumulative_minutes += duration
            if episode_start is None:
                episode_start = start
        elif episode_start is not None:
            longest_timeout = max(longest_timeout, minutes(start - episode_start))
            episode_start = None

    if episode_start is not None:
        longest_timeout = max(longest_timeout, minutes(window_end - episode_start))

    rows = []
    if cumulative_minutes > int(rules["cumulative_breach_limit_min"]):
        rows.append(
            {
                "batch_id": batch["batch_id"],
                "route_id": route_id,
                "breach_minutes": cumulative_minutes,
                "breach_type": "cumulative_over_limit",
            }
        )

    if longest_timeout > int(rules["recovery_limit_min"]):
        rows.append(
            {
                "batch_id": batch["batch_id"],
                "route_id": route_id,
                "breach_minutes": longest_timeout,
                "breach_type": "recovery_timeout",
            }
        )

    return rows


sheets = pd.read_excel(INPUT_PATH, sheet_name=None, engine="openpyxl")
route_sla = sheets["Route SLA"].copy()
trips = sheets["Trips"].copy()
batch_map = sheets["Batch Map"].copy()
sensor_log = sheets["Sensor Log"].copy()

for frame, cols in (
    (trips, ["depart_ts", "arrive_ts"]),
    (batch_map, ["load_end_ts", "handoff_ts"]),
    (sensor_log, ["reading_ts"]),
):
    for column in cols:
        frame[column] = pd.to_datetime(frame[column])

sla_by_route = route_sla.set_index("route_id").to_dict(orient="index")
trips_by_id = trips.set_index("trip_id").to_dict(orient="index")

sensor_log = sensor_log.sort_values(["sensor_id", "reading_ts"], kind="mergesort")
readings_by_sensor = {}
for sensor_id, group in sensor_log.groupby("sensor_id", sort=False):
    readings_by_sensor[sensor_id] = group.to_dict(orient="records")

results = []
for batch in batch_map.to_dict(orient="records"):
    results.extend(evaluate_batch(batch, trips_by_id, sla_by_route, readings_by_sensor))

output = pd.DataFrame(results, columns=["batch_id", "route_id", "breach_minutes", "breach_type"])
if output.empty:
    output = pd.DataFrame(columns=["batch_id", "route_id", "breach_minutes", "breach_type"])
else:
    output = output.sort_values(["route_id", "batch_id", "breach_type"], kind="mergesort").reset_index(drop=True)
    output["breach_minutes"] = output["breach_minutes"].astype(int)

output.to_csv(OUTPUT_PATH, index=False)
PY
