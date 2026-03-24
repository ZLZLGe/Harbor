#!/usr/bin/env python3

from pathlib import Path

import numpy as np
import pandas as pd


INPUT_ARCHIVE = Path("/root/data/commissioning_segments.npz")
MANIFEST_FILE = Path("/root/data/segment_manifest.csv")
OUTPUT_FILE = Path("/root/commissioning_noise_baseline.csv")
TARGET_SAMPLE_RATE_HZ = 1024
HIGHPASS_CUTOFF_HZ = 20.0
CROP_SECONDS = 2.0
WELCH_WINDOW_SECONDS = 2.0


def condition_and_summarize(segment_id: str, raw_sample_rate_hz: int, strain: np.ndarray) -> dict:
    fft_data = np.fft.rfft(strain)
    freqs = np.fft.rfftfreq(len(strain), d=1.0 / raw_sample_rate_hz)
    fft_data[freqs < HIGHPASS_CUTOFF_HZ] = 0.0
    filtered = np.fft.irfft(fft_data, n=len(strain))

    step = raw_sample_rate_hz // TARGET_SAMPLE_RATE_HZ
    resampled = filtered[::step]

    crop_samples = int(CROP_SECONDS * TARGET_SAMPLE_RATE_HZ)
    cropped = resampled[crop_samples : len(resampled) - crop_samples]

    dt = 1.0 / TARGET_SAMPLE_RATE_HZ
    window_samples = int(WELCH_WINDOW_SECONDS * TARGET_SAMPLE_RATE_HZ)
    hop_samples = window_samples // 2
    window = np.hanning(window_samples)
    scale = 2.0 * dt / np.sum(window**2)

    psd_chunks = []
    for start in range(0, len(cropped) - window_samples + 1, hop_samples):
        piece = cropped[start : start + window_samples]
        psd_chunk = scale * np.abs(np.fft.rfft(piece * window)) ** 2
        psd_chunks.append(psd_chunk)

    avg_psd = np.mean(psd_chunks, axis=0)
    psd_freqs = np.fft.rfftfreq(window_samples, d=dt)

    def band_mean(low_hz: float, high_hz: float) -> float:
        band = (psd_freqs >= low_hz) & (psd_freqs <= high_hz) & (psd_freqs > 0.0)
        return float(avg_psd[band].mean())

    mean_psd_20_200 = band_mean(20.0, 200.0)
    mean_psd_200_500 = band_mean(200.0, 500.0)
    baseline_score = 0.5 * (mean_psd_20_200 + mean_psd_200_500)

    return {
        "segment_id": segment_id,
        "raw_sample_rate_hz": raw_sample_rate_hz,
        "conditioned_sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
        "usable_duration_s": len(cropped) / TARGET_SAMPLE_RATE_HZ,
        "mean_psd_20_200": mean_psd_20_200,
        "mean_psd_200_500": mean_psd_200_500,
        "baseline_score": baseline_score,
    }


def main() -> None:
    manifest = pd.read_csv(MANIFEST_FILE)
    archive = np.load(INPUT_ARCHIVE)

    rows = []
    for record in manifest.to_dict(orient="records"):
        segment_id = record["segment_id"]
        raw_sample_rate_hz = int(record["raw_sample_rate_hz"])
        strain = archive[segment_id]
        rows.append(condition_and_summarize(segment_id, raw_sample_rate_hz, strain))

    rows = sorted(rows, key=lambda row: (row["baseline_score"], row["segment_id"]))
    for quiet_rank, row in enumerate(rows, start=1):
        row["quiet_rank"] = quiet_rank

    output = pd.DataFrame(
        rows,
        columns=[
            "segment_id",
            "raw_sample_rate_hz",
            "conditioned_sample_rate_hz",
            "usable_duration_s",
            "mean_psd_20_200",
            "mean_psd_200_500",
            "baseline_score",
            "quiet_rank",
        ],
    )
    output.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
