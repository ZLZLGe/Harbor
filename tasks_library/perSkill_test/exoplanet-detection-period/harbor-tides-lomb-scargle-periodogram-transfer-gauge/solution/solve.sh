#!/bin/bash
set -e

python3 <<'PY'
from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

MIN_PERIOD_HOURS = 8.0
MAX_PERIOD_HOURS = 30.0
MIN_SEPARATION_HOURS = 0.35
GRID_SIZE = 70000


def ensure_input_path() -> Path:
    candidates = [
        Path("/root/data/harbor_gauge.csv"),
        Path("environment/data/harbor_gauge.csv"),
    ]
    for candidate in candidates:
        try:
            exists = candidate.exists()
        except PermissionError:
            exists = False
        if exists:
            return candidate

    generator = Path("environment/scripts/generate_harbor_gauge.py")
    generated = Path("environment/data/harbor_gauge.csv")
    if generator.exists():
        generated.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([sys.executable, str(generator), str(generated)])
        return generated

    raise FileNotFoundError("Missing harbor_gauge.csv")


def load_series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    times = []
    values = []
    reference_time = None

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["qc_flag"] != "ok":
                continue

            timestamp = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
            if reference_time is None:
                reference_time = timestamp

            delta_hours = (timestamp - reference_time).total_seconds() / 3600.0
            corrected_level = float(row["water_level_m"]) - float(row["sensor_offset_m"])
            times.append(delta_hours)
            values.append(corrected_level)

    return np.asarray(times, dtype=float), np.asarray(values, dtype=float)


def compute_top_peaks(times: np.ndarray, values: np.ndarray) -> list[tuple[float, float]]:
    periods = np.linspace(MIN_PERIOD_HOURS, MAX_PERIOD_HOURS, GRID_SIZE)
    centered = values - values.mean()
    rss0 = float(np.sum(np.square(centered)))
    powers = np.empty_like(periods)

    for index, period in enumerate(periods):
        omega = 2.0 * np.pi / period
        design = np.column_stack(
            [
                np.sin(omega * times),
                np.cos(omega * times),
                np.ones_like(times),
            ]
        )
        coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
        residual = values - design @ coefficients
        rss = float(np.sum(np.square(residual)))
        powers[index] = 1.0 - rss / rss0

    peak_mask = (powers[1:-1] > powers[:-2]) & (powers[1:-1] > powers[2:])
    peak_indices = np.flatnonzero(peak_mask) + 1

    peaks: list[tuple[float, float]] = []
    for peak_index in sorted(peak_indices, key=lambda item: powers[item], reverse=True):
        period = float(periods[peak_index])
        power = float(powers[peak_index])
        if all(abs(period - existing_period) >= MIN_SEPARATION_HOURS for existing_period, _ in peaks):
            peaks.append((period, power))
        if len(peaks) == 3:
            return peaks

    raise RuntimeError("Failed to find three distinct peaks")


input_path = ensure_input_path()
times, values = load_series(input_path)
peaks = compute_top_peaks(times, values)

with Path("/root/tide_peak_table.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["rank", "period_hours", "power"])
    for rank, (period, power) in enumerate(peaks, start=1):
        writer.writerow([rank, f"{period:.5f}", f"{power:.5f}"])
PY
