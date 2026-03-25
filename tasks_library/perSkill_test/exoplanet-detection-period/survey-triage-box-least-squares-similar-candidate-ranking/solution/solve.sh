#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os

import astropy.units as u
import numpy as np
from astropy.timeseries import BoxLeastSquares


DATA_PATH = "/root/data/survey_candidates.csv"
OUTPUT_PATH = "/root/output/transit_candidate_summary.json"
MIN_PERIOD = 1.5 * u.day
MAX_PERIOD = 8.0 * u.day
DURATIONS = np.linspace(1.5, 5.5, 24) * u.hour


def scalar(value: object) -> float:
    if hasattr(value, "value"):
        value = value.value
    array = np.asarray(value)
    return float(array.reshape(-1)[0])


data = np.genfromtxt(DATA_PATH, delimiter=",", names=True, dtype=None, encoding="utf-8")
best_candidate = None

for star_id in np.unique(data["star_id"]):
    mask = data["star_id"] == star_id
    time = data["time_days"][mask] * u.day
    flux = data["flux"][mask]
    flux_err = data["flux_err"][mask]

    model = BoxLeastSquares(time, flux, dy=flux_err)
    periodogram = model.autopower(
        DURATIONS,
        minimum_period=MIN_PERIOD,
        maximum_period=MAX_PERIOD,
        objective="snr",
    )

    best_idx = int(np.argmax(periodogram.power))
    period = periodogram.period[best_idx]
    duration = periodogram.duration[best_idx]
    transit_time = periodogram.transit_time[best_idx]
    peak_power = float(periodogram.power[best_idx])

    stats = model.compute_stats(period, duration, transit_time)
    depth_ppt = abs(scalar(stats["depth"])) * 1000.0

    candidate = {
        "star_id": str(star_id),
        "period_days": period.to_value(u.day),
        "duration_hours": duration.to_value(u.hour),
        "depth_ppt": depth_ppt,
        "peak_power": peak_power,
    }

    if best_candidate is None or candidate["peak_power"] > best_candidate["peak_power"]:
        best_candidate = candidate

rounded = {
    "star_id": best_candidate["star_id"],
    "period_days": round(best_candidate["period_days"], 5),
    "duration_hours": round(best_candidate["duration_hours"], 5),
    "depth_ppt": round(best_candidate["depth_ppt"], 5),
    "peak_power": round(best_candidate["peak_power"], 5),
}

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(rounded, f, ensure_ascii=True, indent=2)
    f.write("\n")
PY
