#!/usr/bin/env python3

import os
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(os.environ.get("CANDIDATE_SEGMENT_FILE", "/root/data/candidate_segment.csv"))
OUTPUT_FILE = Path(
    os.environ.get(
        "TASK_OUTPUT_FILE",
        os.environ.get("CANDIDATE_SUMMARY_FILE", "/root/candidate_conditioning_summary.csv"),
    )
)
RAW_SAMPLE_RATE_HZ = 8192.0
TARGET_SAMPLE_RATE_HZ = 2048.0
HIGH_PASS_CUTOFF_HZ = 20.0
CROP_SECONDS = 1.5


def highpass_frequency_domain(strain: np.ndarray, sample_rate_hz: float, cutoff_hz: float) -> np.ndarray:
    fft_data = np.fft.rfft(strain)
    freqs = np.fft.rfftfreq(len(strain), d=1.0 / sample_rate_hz)
    fft_data[freqs < cutoff_hz] = 0.0
    return np.fft.irfft(fft_data, n=len(strain))


def mean_band_psd(strain: np.ndarray, sample_rate_hz: float, low_hz: float, high_hz: float) -> float:
    sample_count = len(strain)
    dt = 1.0 / sample_rate_hz
    psd = 2.0 * dt / sample_count * np.abs(np.fft.rfft(strain)) ** 2
    freqs = np.fft.rfftfreq(sample_count, d=dt)
    band = (freqs >= low_hz) & (freqs <= high_hz) & (freqs > 0.0)
    return float(psd[band].mean())


def main() -> None:
    raw = pd.read_csv(INPUT_FILE)
    strain = raw["strain"].to_numpy(dtype=float)

    filtered = highpass_frequency_domain(strain, RAW_SAMPLE_RATE_HZ, HIGH_PASS_CUTOFF_HZ)
    downsample_factor = int(RAW_SAMPLE_RATE_HZ / TARGET_SAMPLE_RATE_HZ)
    resampled = filtered[::downsample_factor]

    crop_samples = int(CROP_SECONDS * TARGET_SAMPLE_RATE_HZ)
    cropped = resampled[crop_samples : len(resampled) - crop_samples]

    summary = pd.DataFrame(
        [
            {
                "segment_id": "OBS-CANDIDATE-17",
                "final_sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
                "effective_duration_s": len(cropped) / TARGET_SAMPLE_RATE_HZ,
                "mean_psd_25_40": mean_band_psd(cropped, TARGET_SAMPLE_RATE_HZ, 25.0, 40.0),
                "mean_psd_80_120": mean_band_psd(cropped, TARGET_SAMPLE_RATE_HZ, 80.0, 120.0),
            }
        ]
    )
    summary.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
