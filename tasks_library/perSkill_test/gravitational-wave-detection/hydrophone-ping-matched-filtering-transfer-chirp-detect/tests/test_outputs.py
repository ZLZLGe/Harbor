import csv
import math
import wave
from pathlib import Path

import numpy as np


OUTPUT_PATH = Path("/root/hydrophone_ping_report.csv")
RECORDING_PATH = Path("/root/data/hydrophone_recording.wav")
REFERENCE_DIR = Path("/root/data/reference_chirps")
EXPECTED_COLUMNS = ["pulse_type", "arrival_sample", "peak_response"]


def _load_recording() -> np.ndarray:
    with wave.open(str(RECORDING_PATH), "rb") as wav_file:
        assert wav_file.getnchannels() == 1, "recording must be mono"
        assert wav_file.getsampwidth() == 2, "recording must be 16-bit PCM"
        frames = wav_file.readframes(wav_file.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float64)


def _load_template(path: Path) -> np.ndarray:
    values = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["amplitude"], f"unexpected columns in {path}"
        for row in reader:
            values.append(float(row["amplitude"]))
    return np.asarray(values, dtype=np.float64)


def _expected_rows():
    recording = _load_recording()
    rows = []
    for template_path in sorted(REFERENCE_DIR.glob("*.csv")):
        template = _load_template(template_path)
        response = np.correlate(recording, template, mode="valid")
        arrival_sample = int(np.abs(response).argmax())
        peak_response = float(np.abs(response[arrival_sample]))
        rows.append(
            {
                "pulse_type": template_path.stem,
                "arrival_sample": arrival_sample,
                "peak_response": peak_response,
            }
        )
    rows.sort(key=lambda item: item["arrival_sample"])
    return rows


def _load_output_rows():
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EXPECTED_COLUMNS, (
            f"expected columns {EXPECTED_COLUMNS}, got {reader.fieldnames}"
        )
        rows = []
        for row in reader:
            rows.append(
                {
                    "pulse_type": row["pulse_type"],
                    "arrival_sample": int(row["arrival_sample"]),
                    "peak_response": float(row["peak_response"]),
                }
            )
    return rows


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_output_matches_expected_detection_table():
    expected = _expected_rows()
    actual = _load_output_rows()

    assert len(actual) == 3, f"expected 3 detection rows, got {len(actual)}"
    assert actual == sorted(actual, key=lambda item: item["arrival_sample"]), (
        "rows must be sorted by arrival_sample ascending"
    )

    expected_types = {row["pulse_type"] for row in expected}
    actual_types = {row["pulse_type"] for row in actual}
    assert actual_types == expected_types, "pulse_type values must match the reference files"

    for actual_row, expected_row in zip(actual, expected):
        assert actual_row["pulse_type"] == expected_row["pulse_type"]
        assert actual_row["arrival_sample"] == expected_row["arrival_sample"]
        assert math.isfinite(actual_row["peak_response"])
        assert math.isclose(
            actual_row["peak_response"],
            expected_row["peak_response"],
            rel_tol=0.0,
            abs_tol=1e-3,
        )
