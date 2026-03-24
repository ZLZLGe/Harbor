import json
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_FILE = Path("/root/hydrophone_window_quality.csv")
INPUT_FILE = Path("/root/data/hydrophone_pressure.npy")
MANIFEST_FILE = Path("/root/data/window_manifest.json")
EXPECTED_COLUMNS = [
    "window_id",
    "start_time_s",
    "end_time_s",
    "conditioned_sample_rate_hz",
    "usable_duration_s",
    "mean_psd_25_60",
    "mean_psd_120_240",
    "low_frequency_noise_ratio",
    "search_ready",
]


def build_expected() -> tuple[pd.DataFrame, float]:
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

        samples = pressure[start_index:end_index]
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
        hann = np.hanning(window_samples)
        scale = 2.0 * dt / np.sum(hann**2)

        psd_chunks = []
        for start in range(0, len(cropped) - window_samples + 1, hop_samples):
            piece = cropped[start : start + window_samples]
            psd_chunks.append(scale * np.abs(np.fft.rfft(hann * piece)) ** 2)

        average_psd = np.mean(psd_chunks, axis=0)
        psd_freqs = np.fft.rfftfreq(window_samples, d=dt)

        low_mask = (psd_freqs >= 25.0) & (psd_freqs <= 60.0) & (psd_freqs > 0.0)
        search_mask = (psd_freqs >= 120.0) & (psd_freqs <= 240.0) & (psd_freqs > 0.0)
        mean_psd_25_60 = float(average_psd[low_mask].mean())
        mean_psd_120_240 = float(average_psd[search_mask].mean())
        ratio = mean_psd_25_60 / mean_psd_120_240

        rows.append(
            {
                "window_id": window["window_id"],
                "start_time_s": start_time_s,
                "end_time_s": end_time_s,
                "conditioned_sample_rate_hz": target_sample_rate_hz,
                "usable_duration_s": len(cropped) / target_sample_rate_hz,
                "mean_psd_25_60": mean_psd_25_60,
                "mean_psd_120_240": mean_psd_120_240,
                "low_frequency_noise_ratio": ratio,
                "search_ready": "READY" if ratio <= threshold else "HOLD",
            }
        )

    return pd.DataFrame(rows, columns=EXPECTED_COLUMNS), threshold


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_output_matches_expected():
    output = pd.read_csv(OUTPUT_FILE)
    expected, _ = build_expected()

    assert list(output.columns) == EXPECTED_COLUMNS
    assert len(output) == len(expected) == 6
    assert output["window_id"].tolist() == expected["window_id"].tolist()
    assert output["search_ready"].tolist() == expected["search_ready"].tolist()

    for column in ["conditioned_sample_rate_hz"]:
        assert output[column].astype(int).tolist() == expected[column].astype(int).tolist()

    for column in [
        "start_time_s",
        "end_time_s",
        "usable_duration_s",
        "mean_psd_25_60",
        "mean_psd_120_240",
        "low_frequency_noise_ratio",
    ]:
        assert np.allclose(output[column], expected[column], rtol=1e-6, atol=0.0), column


def test_window_order_and_ready_split():
    output = pd.read_csv(OUTPUT_FILE)

    assert output["window_id"].tolist() == ["HP-00", "HP-01", "HP-02", "HP-03", "HP-04", "HP-05"]
    assert output["start_time_s"].tolist() == [0.0, 6.0, 12.0, 18.0, 24.0, 30.0]
    assert output["search_ready"].tolist() == ["READY", "HOLD", "READY", "HOLD", "READY", "HOLD"]
    assert (output["conditioned_sample_rate_hz"] == 600).all()
    assert np.allclose(output["usable_duration_s"], 5.0, rtol=0.0, atol=1e-9)


def test_ratio_definition_and_threshold_rule():
    output = pd.read_csv(OUTPUT_FILE)
    _, threshold = build_expected()

    reconstructed_ratio = output["mean_psd_25_60"] / output["mean_psd_120_240"]
    assert np.allclose(output["low_frequency_noise_ratio"], reconstructed_ratio, rtol=1e-12, atol=0.0)

    expected_status = ["READY" if value <= threshold else "HOLD" for value in output["low_frequency_noise_ratio"]]
    assert output["search_ready"].tolist() == expected_status
    assert (output.loc[output["search_ready"] == "READY", "low_frequency_noise_ratio"] <= threshold).all()
    assert (output.loc[output["search_ready"] == "HOLD", "low_frequency_noise_ratio"] > threshold).all()
