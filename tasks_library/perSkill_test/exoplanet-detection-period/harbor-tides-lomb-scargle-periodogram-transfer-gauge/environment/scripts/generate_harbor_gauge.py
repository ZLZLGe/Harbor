from __future__ import annotations

import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

SEED = 20260325
START_TIME = datetime(2024, 7, 1, tzinfo=timezone.utc)
SEARCH_PERIODS_HOURS = [12.42, 24.84, 12.0]
AMPLITUDES = [1.1, 0.7, 0.45]
PHASES = [0.4, -0.7, 1.1]
GAP_WINDOWS_HOURS = [(36, 52), (118, 146), (241, 260), (310, 330)]
SURGE_CENTERS_HOURS = [88, 205, 287]


def build_rows() -> list[dict[str, str]]:
    rng = np.random.default_rng(SEED)
    base_hours = np.arange(0.0, 16.0 * 24.0, 0.5)

    keep_mask = np.ones_like(base_hours, dtype=bool)
    for start, end in GAP_WINDOWS_HOURS:
        keep_mask &= ~((base_hours >= start) & (base_hours <= end))
    keep_mask &= rng.random(base_hours.size) > 0.18

    times = base_hours[keep_mask]
    level = np.zeros_like(times)
    for amplitude, period, phase in zip(AMPLITUDES, SEARCH_PERIODS_HOURS, PHASES):
        level += amplitude * np.sin(2.0 * np.pi * times / period + phase)

    level += 0.02 * np.sin(2.0 * np.pi * times / 6.21 + 0.3)
    level += 0.03 * rng.normal(size=times.size)

    qc_flags = np.full(times.shape, "ok", dtype=object)
    for center in SURGE_CENTERS_HOURS:
        spike_index = int(np.argmin(np.abs(times - center)))
        level[spike_index] += 0.7
        qc_flags[spike_index] = "suspect"

    offsets = np.where(times < 190.0, 0.12, -0.04)
    observed = level + offsets

    rows: list[dict[str, str]] = []
    for hour, water_level, offset, qc_flag in zip(times, observed, offsets, qc_flags):
        timestamp = START_TIME + timedelta(hours=float(hour))
        rows.append(
            {
                "timestamp_utc": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "water_level_m": f"{water_level:.5f}",
                "sensor_offset_m": f"{offset:.2f}",
                "qc_flag": str(qc_flag),
            }
        )
    return rows


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/data/harbor_gauge.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp_utc", "water_level_m", "sensor_offset_m", "qc_flag"],
        )
        writer.writeheader()
        writer.writerows(build_rows())


if __name__ == "__main__":
    main()
