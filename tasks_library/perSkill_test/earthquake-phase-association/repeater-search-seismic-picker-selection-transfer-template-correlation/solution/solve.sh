#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/root/data}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/repeater_detections.csv}"

python3 <<'PY'
import csv
import math
import os
from datetime import datetime, timedelta


DATA_DIR = os.environ.get("DATA_DIR", "/root/data")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/repeater_detections.csv")
SEED_CATALOG = os.path.join(DATA_DIR, "seed_catalog.csv")
CONTINUOUS = os.path.join(DATA_DIR, "continuous_waveforms.csv")


def read_wide_waveform_csv(path, time_column):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        columns = [name for name in reader.fieldnames if name != time_column]
        times = []
        series = {name: [] for name in columns}
        for row in reader:
            times.append(row[time_column])
            for name in columns:
                series[name].append(float(row[name]))
    return times, columns, series


def read_template(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        columns = [name for name in reader.fieldnames if name != "relative_time_s"]
        rows = []
        for row in reader:
            rows.append([float(row[name]) for name in columns])
    return columns, rows


def precompute_template(rows):
    template_len = len(rows)
    channel_count = len(rows[0])
    centered = []
    weights = []
    for channel_idx in range(channel_count):
        values = [rows[row_idx][channel_idx] for row_idx in range(template_len)]
        mean_val = sum(values) / template_len
        centered_values = [value - mean_val for value in values]
        norm = math.sqrt(sum(value * value for value in centered_values))
        centered.append(centered_values)
        weights.append(norm)
    return centered, weights


def score_window(series, columns, start_idx, template_centered, template_weights, template_len):
    weighted_score = 0.0
    weight_sum = 0.0
    for channel_idx, name in enumerate(columns):
        weight = template_weights[channel_idx]
        if weight == 0.0:
            continue
        segment = series[name][start_idx : start_idx + template_len]
        segment_mean = sum(segment) / template_len
        dot = 0.0
        segment_energy = 0.0
        template_values = template_centered[channel_idx]
        for seg_value, tpl_value in zip(segment, template_values):
            centered_value = seg_value - segment_mean
            dot += centered_value * tpl_value
            segment_energy += centered_value * centered_value
        if segment_energy == 0.0:
            continue
        corr = dot / (math.sqrt(segment_energy) * weight)
        weighted_score += corr * weight
        weight_sum += weight
    if weight_sum == 0.0:
        return 0.0
    return weighted_score / weight_sum


def is_local_maximum(scores, idx, radius):
    left = max(0, idx - radius)
    right = min(len(scores), idx + radius + 1)
    return scores[idx] >= max(scores[left:right])


def seconds_between(a, b):
    return abs((a - b).total_seconds())


times, continuous_columns, continuous_series = read_wide_waveform_csv(CONTINUOUS, "time")
start_time = datetime.fromisoformat(times[0])
sample_dt = (
    datetime.fromisoformat(times[1]) - datetime.fromisoformat(times[0])
).total_seconds()

seed_rows = []
with open(SEED_CATALOG, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        seed_rows.append(row)

seed_times = [datetime.fromisoformat(row["seed_time"]) for row in seed_rows]

all_candidates = []
for seed in seed_rows:
    template_path = os.path.join(DATA_DIR, seed["template_file"])
    template_columns, template_rows = read_template(template_path)
    if template_columns != continuous_columns:
        raise ValueError(f"Template columns do not match continuous record for {template_path}")

    template_centered, template_weights = precompute_template(template_rows)
    template_len = len(template_rows)
    scores = []
    for start_idx in range(len(times) - template_len + 1):
        scores.append(
            score_window(
                continuous_series,
                continuous_columns,
                start_idx,
                template_centered,
                template_weights,
                template_len,
            )
        )

    threshold = 0.76 if seed["family_id"] == "A" else 0.74
    local_radius = 8
    for idx, score in enumerate(scores):
        if score < threshold:
            continue
        if not is_local_maximum(scores, idx, local_radius):
            continue
        detection_time = start_time + timedelta(seconds=idx * sample_dt)
        all_candidates.append(
            {
                "detection_time": detection_time,
                "matched_family": seed["family_id"],
                "score": score,
            }
        )

all_candidates.sort(key=lambda row: row["score"], reverse=True)

accepted = []
for candidate in all_candidates:
    if any(seconds_between(candidate["detection_time"], seed_time) <= 0.75 for seed_time in seed_times):
        continue
    if any(seconds_between(candidate["detection_time"], item["detection_time"]) <= 0.75 for item in accepted):
        continue
    accepted.append(candidate)

accepted.sort(key=lambda row: row["detection_time"])

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["detection_time", "matched_family", "score"])
    writer.writeheader()
    for row in accepted:
        writer.writerow(
            {
                "detection_time": row["detection_time"].isoformat(timespec="milliseconds"),
                "matched_family": row["matched_family"],
                "score": f"{row['score']:.4f}",
            }
        )
PY
