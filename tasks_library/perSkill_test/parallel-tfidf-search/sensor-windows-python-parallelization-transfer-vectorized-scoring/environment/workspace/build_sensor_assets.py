#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


OUTPUT_DIR = Path(__file__).resolve().parent
WINDOW_FILE = OUTPUT_DIR / "sensor_windows.npz"
MANIFEST_FILE = OUTPUT_DIR / "window_manifest.json"


def build_windows() -> None:
    rng = np.random.default_rng(240325)

    num_windows = 4800
    window_size = 192
    rolling_width = 24
    device_count = 24

    ticks = np.arange(window_size, dtype=np.float64)
    base_level = rng.normal(55.0, 5.5, size=(num_windows, 1))
    amplitude = rng.uniform(2.5, 6.8, size=(num_windows, 1))
    phase = rng.uniform(0.0, 2.0 * np.pi, size=(num_windows, 1))
    drift = rng.normal(0.0, 0.035, size=(num_windows, 1))
    noise = rng.normal(0.0, 0.85, size=(num_windows, window_size))

    seasonal = amplitude * np.sin((ticks[None, :] / 11.5) + phase)
    trend = drift * (ticks[None, :] - (window_size / 2.0))
    windows = base_level + seasonal + trend + noise

    spike_mask = rng.random((num_windows, window_size)) < 0.014
    spike_values = rng.normal(0.0, 8.5, size=(num_windows, window_size))
    windows = windows + spike_mask * spike_values

    ramp_mask = rng.random(num_windows) < 0.17
    ramps = np.linspace(0.0, 5.75, window_size, dtype=np.float64)
    windows[ramp_mask] = windows[ramp_mask] + ramps

    drop_mask = rng.random(num_windows) < 0.11
    windows[drop_mask, 76:104] = windows[drop_mask, 76:104] - 6.5

    pulse_mask = rng.random(num_windows) < 0.08
    windows[pulse_mask, 124:140] = windows[pulse_mask, 124:140] + 7.0

    window_ids = np.arange(410_000, 410_000 + num_windows, dtype=np.int64)
    device_ids = np.array([f"sensor-{index % device_count:02d}" for index in range(num_windows)])
    start_ticks = np.arange(1_000_000, 1_000_000 + num_windows * rolling_width, rolling_width, dtype=np.int64)
    end_ticks = start_ticks + window_size - 1

    np.savez_compressed(
        WINDOW_FILE,
        measurements=windows.astype(np.float64),
        window_ids=window_ids,
        device_ids=device_ids,
        start_ticks=start_ticks,
        end_ticks=end_ticks,
    )

    manifest = {
        "batch_id": "yard-batch-2026-03-25",
        "rolling_width": rolling_width,
        "threshold_z": 2.35,
        "volatility_floor": 0.65,
        "spike_top_n": 6,
        "spike_weight": 0.62,
        "drift_weight": 0.24,
        "breach_weight": 0.14,
        "severity_thresholds": {
            "watch": 1.20,
            "elevated": 1.85,
            "critical": 2.60,
        },
        "top_summary_count": 8,
        "hotspot_count": 5,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_windows()
