import os
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(os.environ.get("TASK_INPUT_FILE", "/root/data/candidate_segment.csv"))
OUTPUT_FILE = Path(os.environ.get("TASK_OUTPUT_FILE", "/root/candidate_conditioning_summary.csv"))
EXPECTED_FILE = Path(os.environ.get("TASK_EXPECTED_FILE", "/tests/expected_summary.csv"))
EXPECTED_COLUMNS = [
    "segment_id",
    "final_sample_rate_hz",
    "effective_duration_s",
    "mean_psd_25_40",
    "mean_psd_80_120",
]


def build_expected_summary():
    raw = pd.read_csv(INPUT_FILE)
    raw_sample_rate_hz = 8192.0
    target_sample_rate_hz = 2048.0
    cutoff_hz = 20.0
    crop_seconds = 1.5

    strain = raw["strain"].to_numpy(dtype=float)
    fft_data = np.fft.rfft(strain)
    freqs = np.fft.rfftfreq(len(strain), d=1.0 / raw_sample_rate_hz)
    fft_data[freqs < cutoff_hz] = 0.0
    filtered = np.fft.irfft(fft_data, n=len(strain))

    resampled = filtered[:: int(raw_sample_rate_hz / target_sample_rate_hz)]
    crop_samples = int(crop_seconds * target_sample_rate_hz)
    cropped = resampled[crop_samples : len(resampled) - crop_samples]

    sample_count = len(cropped)
    dt = 1.0 / target_sample_rate_hz
    psd = 2.0 * dt / sample_count * np.abs(np.fft.rfft(cropped)) ** 2
    psd_freqs = np.fft.rfftfreq(sample_count, d=dt)

    def band_mean(low_hz: float, high_hz: float) -> float:
        band = (psd_freqs >= low_hz) & (psd_freqs <= high_hz) & (psd_freqs > 0.0)
        return float(psd[band].mean())

    return {
        "segment_id": "OBS-CANDIDATE-17",
        "final_sample_rate_hz": target_sample_rate_hz,
        "effective_duration_s": sample_count / target_sample_rate_hz,
        "mean_psd_25_40": band_mean(25.0, 40.0),
        "mean_psd_80_120": band_mean(80.0, 120.0),
    }


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_output_schema_and_values():
    output = pd.read_csv(OUTPUT_FILE)
    expected_from_file = pd.read_csv(EXPECTED_FILE)
    assert list(output.columns) == EXPECTED_COLUMNS
    assert len(output) == 1
    assert len(expected_from_file) == 1

    row = output.iloc[0]
    expected_row = expected_from_file.iloc[0]
    expected = build_expected_summary()

    assert row["segment_id"] == expected["segment_id"]
    assert row["segment_id"] == expected_row["segment_id"]
    assert np.isclose(row["final_sample_rate_hz"], expected["final_sample_rate_hz"], rtol=0.0, atol=1e-9)
    assert np.isclose(row["final_sample_rate_hz"], expected_row["final_sample_rate_hz"], rtol=0.0, atol=1e-9)
    assert np.isclose(row["effective_duration_s"], expected["effective_duration_s"], rtol=0.0, atol=1e-9)
    assert np.isclose(row["effective_duration_s"], expected_row["effective_duration_s"], rtol=0.0, atol=1e-9)
    assert np.isclose(row["mean_psd_25_40"], expected["mean_psd_25_40"], rtol=1e-6, atol=0.0)
    assert np.isclose(row["mean_psd_25_40"], expected_row["mean_psd_25_40"], rtol=1e-6, atol=0.0)
    assert np.isclose(row["mean_psd_80_120"], expected["mean_psd_80_120"], rtol=1e-6, atol=0.0)
    assert np.isclose(row["mean_psd_80_120"], expected_row["mean_psd_80_120"], rtol=1e-6, atol=0.0)


def test_psd_columns_are_positive_and_ordered():
    output = pd.read_csv(OUTPUT_FILE)
    row = output.iloc[0]

    assert row["mean_psd_25_40"] > 0.0
    assert row["mean_psd_80_120"] > 0.0
    assert row["mean_psd_80_120"] > row["mean_psd_25_40"]
