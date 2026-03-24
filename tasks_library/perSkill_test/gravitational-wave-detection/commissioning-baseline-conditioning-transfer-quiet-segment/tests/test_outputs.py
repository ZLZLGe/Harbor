from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_FILE = Path("/root/commissioning_noise_baseline.csv")
INPUT_ARCHIVE = Path("/root/data/commissioning_segments.npz")
MANIFEST_FILE = Path("/root/data/segment_manifest.csv")
EXPECTED_COLUMNS = [
    "segment_id",
    "raw_sample_rate_hz",
    "conditioned_sample_rate_hz",
    "usable_duration_s",
    "mean_psd_20_200",
    "mean_psd_200_500",
    "baseline_score",
    "quiet_rank",
]
TARGET_SAMPLE_RATE_HZ = 1024


def build_expected() -> pd.DataFrame:
    manifest = pd.read_csv(MANIFEST_FILE)
    archive = np.load(INPUT_ARCHIVE)
    rows = []

    for record in manifest.to_dict(orient="records"):
        segment_id = record["segment_id"]
        raw_sample_rate_hz = int(record["raw_sample_rate_hz"])
        strain = archive[segment_id]

        freqs = np.fft.rfftfreq(len(strain), d=1.0 / raw_sample_rate_hz)
        fft_data = np.fft.rfft(strain)
        fft_data[freqs < 20.0] = 0.0
        filtered = np.fft.irfft(fft_data, n=len(strain))

        step = raw_sample_rate_hz // TARGET_SAMPLE_RATE_HZ
        resampled = filtered[::step]
        crop_samples = 2 * TARGET_SAMPLE_RATE_HZ
        cropped = resampled[crop_samples : len(resampled) - crop_samples]

        dt = 1.0 / TARGET_SAMPLE_RATE_HZ
        window_samples = 2 * TARGET_SAMPLE_RATE_HZ
        hop_samples = window_samples // 2
        window = np.hanning(window_samples)
        scale = 2.0 * dt / np.sum(window**2)
        psd_chunks = []
        for start in range(0, len(cropped) - window_samples + 1, hop_samples):
            piece = cropped[start : start + window_samples]
            psd_chunks.append(scale * np.abs(np.fft.rfft(piece * window)) ** 2)

        avg_psd = np.mean(psd_chunks, axis=0)
        psd_freqs = np.fft.rfftfreq(window_samples, d=dt)

        band_20_200 = (psd_freqs >= 20.0) & (psd_freqs <= 200.0) & (psd_freqs > 0.0)
        band_200_500 = (psd_freqs >= 200.0) & (psd_freqs <= 500.0) & (psd_freqs > 0.0)
        mean_psd_20_200 = float(avg_psd[band_20_200].mean())
        mean_psd_200_500 = float(avg_psd[band_200_500].mean())
        baseline_score = 0.5 * (mean_psd_20_200 + mean_psd_200_500)

        rows.append(
            {
                "segment_id": segment_id,
                "raw_sample_rate_hz": raw_sample_rate_hz,
                "conditioned_sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
                "usable_duration_s": len(cropped) / TARGET_SAMPLE_RATE_HZ,
                "mean_psd_20_200": mean_psd_20_200,
                "mean_psd_200_500": mean_psd_200_500,
                "baseline_score": baseline_score,
            }
        )

    rows = sorted(rows, key=lambda row: (row["baseline_score"], row["segment_id"]))
    for quiet_rank, row in enumerate(rows, start=1):
        row["quiet_rank"] = quiet_rank

    return pd.DataFrame(rows, columns=EXPECTED_COLUMNS)


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_output_matches_expected():
    output = pd.read_csv(OUTPUT_FILE)
    expected = build_expected()

    assert list(output.columns) == EXPECTED_COLUMNS
    assert len(output) == len(expected)

    for column in ["segment_id"]:
        assert output[column].tolist() == expected[column].tolist()

    for column in ["raw_sample_rate_hz", "conditioned_sample_rate_hz", "quiet_rank"]:
        assert output[column].astype(int).tolist() == expected[column].astype(int).tolist()

    for column in ["usable_duration_s", "mean_psd_20_200", "mean_psd_200_500", "baseline_score"]:
        assert np.allclose(output[column], expected[column], rtol=1e-6, atol=0.0), column


def test_output_is_ranked_and_complete():
    output = pd.read_csv(OUTPUT_FILE)
    manifest = pd.read_csv(MANIFEST_FILE)

    assert output["segment_id"].tolist() == ["COM-B", "COM-A", "COM-C", "COM-D"]
    assert output["quiet_rank"].tolist() == [1, 2, 3, 4]
    assert set(output["segment_id"]) == set(manifest["segment_id"])
    assert (output["conditioned_sample_rate_hz"] == TARGET_SAMPLE_RATE_HZ).all()
    assert (output["usable_duration_s"] == 16.0).all()


def test_baseline_score_definition_and_ordering():
    output = pd.read_csv(OUTPUT_FILE)
    reconstructed = 0.5 * (output["mean_psd_20_200"] + output["mean_psd_200_500"])

    assert np.allclose(output["baseline_score"], reconstructed, rtol=1e-12, atol=0.0)
    assert output["baseline_score"].is_monotonic_increasing
