#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import wave
from pathlib import Path

import numpy as np


DATA_DIR = Path("/root/data")
OUTPUT_PATH = Path("/root/hydrophone_ping_report.csv")


def load_recording(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.readframes(wav_file.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float64)


def load_template(path: Path) -> np.ndarray:
    values = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values.append(float(row["amplitude"]))
    return np.asarray(values, dtype=np.float64)


recording = load_recording(DATA_DIR / "hydrophone_recording.wav")
rows = []
for template_path in sorted((DATA_DIR / "reference_chirps").glob("*.csv")):
    template = load_template(template_path)
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

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["pulse_type", "arrival_sample", "peak_response"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "pulse_type": row["pulse_type"],
                "arrival_sample": row["arrival_sample"],
                "peak_response": f"{row['peak_response']:.6f}",
            }
        )
PY
