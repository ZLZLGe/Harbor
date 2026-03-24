#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path("/root/data/hydrophone_pressure.npy")
MANIFEST_FILE = Path("/root/data/window_manifest.json")
OUTPUT_FILE = Path("/root/hydrophone_window_quality.csv")


def mean_band_psd(psd: np.ndarray, freqs: np.ndarray, low_hz: float, high_hz: float) -> float:
    mask = (freqs >= low_hz) & (freqs <= high_hz) & (freqs > 0.0)
    return float(psd[mask].mean())


def condition_window(samples: np.ndarray, raw_sample_rate_hz: int, target_sample_rate_hz: int) -> tuple[float, float, float]:
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / raw_sample_rate_hz)
    spectrum = np.fft.rfft(samples)
    spectrum[freqs < 25.0] = 0.0
    filtered = np.fft.irfft(spectrum, n=len(samples))

    step = raw_sample_rate_hz // target_sample_rate_hz
    resampled = filtered[::step]

    crop_samples = int(0.5 * target_sample_rate_hz)
    cropped = resampled[crop_samples : len(resampled) - crop_samples]

    dt = 1.0 / target_sample_rate_hz
    window_samples = int(1.0 * target_sample_rate_hz)
    hop_samples = window_samples // 2
    window = np.hanning(window_samples)
    scale = 2.0 * dt / np.sum(window**2)

    psd_chunks = []
    for start in range(0, len(cropped) - window_samples + 1, hop_samples):
        chunk = cropped[start : start + window_samples]
        psd_chunks.append(scale * np.abs(np.fft.rfft(window * chunk)) ** 2)

    average_psd = np.mean(psd_chunks, axis=0)
    psd_freqs = np.fft.rfftfreq(window_samples, d=dt)

    mean_psd_25_60 = mean_band_psd(average_psd, psd_freqs, 25.0, 60.0)
    mean_psd_120_240 = mean_band_psd(average_psd, psd_freqs, 120.0, 240.0)
    usable_duration_s = len(cropped) / target_sample_rate_hz

    return usable_duration_s, mean_psd_25_60, mean_psd_120_240


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    pressure = np.load(INPUT_FILE)

    raw_sample_rate_hz = int(manifest["raw_sample_rate_hz"])
    target_sample_rate_hz = int(manifest["target_sample_rate_hz"])
    threshold = float(manifest["max_low_frequency_noise_ratio"])

    rows = []
    for window in sorted(manifest["windows"], key=lambda item: item["start_time_s"]):
        start_time_s = float(window["start_time_s"])
        end_time_s = float(window["end_time_s"])
        start_index = int(round(start_time_s * raw_sample_rate_hz))
        end_index = int(round(end_time_s * raw_sample_rate_hz))

        usable_duration_s, mean_psd_25_60, mean_psd_120_240 = condition_window(
            pressure[start_index:end_index],
            raw_sample_rate_hz,
            target_sample_rate_hz,
        )
        low_frequency_noise_ratio = mean_psd_25_60 / mean_psd_120_240

        rows.append(
            {
                "window_id": window["window_id"],
                "start_time_s": start_time_s,
                "end_time_s": end_time_s,
                "conditioned_sample_rate_hz": target_sample_rate_hz,
                "usable_duration_s": usable_duration_s,
                "mean_psd_25_60": mean_psd_25_60,
                "mean_psd_120_240": mean_psd_120_240,
                "low_frequency_noise_ratio": low_frequency_noise_ratio,
                "search_ready": "READY" if low_frequency_noise_ratio <= threshold else "HOLD",
            }
        )

    pd.DataFrame(
        rows,
        columns=[
            "window_id",
            "start_time_s",
            "end_time_s",
            "conditioned_sample_rate_hz",
            "usable_duration_s",
            "mean_psd_25_60",
            "mean_psd_120_240",
            "low_frequency_noise_ratio",
            "search_ready",
        ],
    ).sort_values("start_time_s").to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
