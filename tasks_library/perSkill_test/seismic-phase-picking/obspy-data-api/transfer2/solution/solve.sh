#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

import numpy as np
from obspy import Stream, Trace

DATA_DIR = Path("/root/data")
REFERENCE_PATH = DATA_DIR / "phase_reference.csv"
OUTPUT_PATH = Path("/root/transfer2_signal_audit.csv")


def load_payload(npz_path: Path):
    return np.load(npz_path, allow_pickle=False)


def load_stream(payload) -> Stream:
    waveform = payload["data"].astype(np.float64)
    channels = [part.strip() for part in str(payload["channels"]).split(",") if part.strip()]
    if len(channels) < waveform.shape[1]:
        channels.extend(f"CH{index + 1}" for index in range(len(channels), waveform.shape[1]))
    channels = channels[: waveform.shape[1]]

    stream = Stream()
    for column_index in range(waveform.shape[1]):
        trace = Trace(data=waveform[:, column_index])
        trace.stats.channel = channels[column_index]
        trace.stats.sampling_rate = 1.0 / float(payload["dt"])
        stream.append(trace)
    return stream


def rms_scaled(block: np.ndarray) -> float:
    return round(float(np.sqrt(np.mean(np.square(block)))) * 1e10, 6)


rows = []
with REFERENCE_PATH.open(encoding="utf-8", newline="") as handle:
    references = sorted(csv.DictReader(handle), key=lambda row: row["file_name"])

for reference in references:
    file_name = reference["file_name"]
    p_idx = int(reference["p_idx"])
    s_idx = int(reference["s_idx"])
    payload = load_payload(DATA_DIR / file_name)
    stream = load_stream(payload)
    waveform = np.stack([trace.data for trace in stream], axis=1)
    dt = float(payload["dt"])

    pre_block = waveform[p_idx - 400 : p_idx - 100, :]
    arrival_block = waveform[p_idx : s_idx + 1, :]
    coda_block = waveform[s_idx + 50 : s_idx + 350, :]

    pre_rms = float(np.sqrt(np.mean(np.square(pre_block))))
    arrival_rms = float(np.sqrt(np.mean(np.square(arrival_block))))
    coda_rms = float(np.sqrt(np.mean(np.square(coda_block))))
    dominant_channel_index = int(np.argmax(np.max(np.abs(arrival_block), axis=0)))

    rows.append(
        {
            "file_name": file_name,
            "pre_rms_scaled": f"{rms_scaled(pre_block):.6f}",
            "arrival_rms_scaled": f"{rms_scaled(arrival_block):.6f}",
            "coda_rms_scaled": f"{rms_scaled(coda_block):.6f}",
            "arrival_to_pre_ratio": f"{round(arrival_rms / pre_rms, 6):.6f}",
            "coda_to_pre_ratio": f"{round(coda_rms / pre_rms, 6):.6f}",
            "dominant_channel": str(stream[dominant_channel_index].stats.channel),
            "s_minus_p_seconds": f"{round((s_idx - p_idx) * dt, 3):.3f}",
            "first_motion": str(payload["first_motion"]),
        }
    )

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "file_name",
            "pre_rms_scaled",
            "arrival_rms_scaled",
            "coda_rms_scaled",
            "arrival_to_pre_ratio",
            "coda_to_pre_ratio",
            "dominant_channel",
            "s_minus_p_seconds",
            "first_motion",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
