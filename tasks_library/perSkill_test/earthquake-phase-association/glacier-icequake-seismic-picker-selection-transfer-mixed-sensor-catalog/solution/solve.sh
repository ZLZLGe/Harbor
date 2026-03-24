#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("/root/data")
OUTPUT_CSV = Path("/root/icequake_candidates.csv")
METHOD_TXT = Path("/root/icequake_method.txt")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


with (DATA_DIR / "approach_scorecard.csv").open(newline="") as handle:
    score_rows = list(csv.DictReader(handle))

selected_family = max(score_rows, key=lambda row: float(row["fit_score"]))["approach_family"]

with (DATA_DIR / "maintenance_windows.csv").open(newline="") as handle:
    maintenance_windows = [
        (parse_time(row["window_start"]), parse_time(row["window_end"]), row["reason"])
        for row in csv.DictReader(handle)
    ]


def in_maintenance_window(event_time: datetime) -> bool:
    return any(start <= event_time <= end for start, end, _ in maintenance_windows)


with (DATA_DIR / "candidate_icequakes.csv").open(newline="") as handle:
    candidate_rows = list(csv.DictReader(handle))

accepted = []
for row in candidate_rows:
    if row["approach_family"] != selected_family:
        continue

    event_time = parse_time(row["time"])
    if in_maintenance_window(event_time):
        continue
    if row["calibration_flag"] != "0":
        continue
    if int(row["support_stations"]) < 3:
        continue
    if int(row["sensor_class_count"]) < 2:
        continue
    if float(row["median_pick_probability"]) < 0.75:
        continue
    if float(row["network_coherence"]) < 0.70:
        continue

    accepted.append(
        {
            "time": row["time"],
            "approach_family": row["approach_family"],
            "support_stations": row["support_stations"],
            "sensor_class_count": row["sensor_class_count"],
            "sensor_types": row["sensor_types"],
            "median_pick_probability": row["median_pick_probability"],
            "network_coherence": row["network_coherence"],
            "comment": row["comment"],
        }
    )

accepted.sort(key=lambda row: row["time"])

METHOD_TXT.write_text(
    "Use a deep-learning picker with multi-station association because the glacier deployment has mixed broadband, "
    "high-gain, and accelerometer channels, there is no local template catalog yet, and simple STA/LTA triggering "
    "produces too many meltwater and calibration false positives for a first-pass review list.\n",
    encoding="utf-8",
)

with OUTPUT_CSV.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "time",
            "approach_family",
            "support_stations",
            "sensor_class_count",
            "sensor_types",
            "median_pick_probability",
            "network_coherence",
            "comment",
        ],
    )
    writer.writeheader()
    writer.writerows(accepted)
PY
