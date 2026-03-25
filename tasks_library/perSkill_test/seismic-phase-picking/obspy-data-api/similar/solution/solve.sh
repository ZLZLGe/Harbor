#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime

DATA_DIR = Path("/root/data")
REFERENCE_PATH = DATA_DIR / "phase_reference.csv"
OUTPUT_PATH = Path("/root/similar_phase_timeline.csv")


def load_stream(npz_path: Path) -> Stream:
    payload = np.load(npz_path, allow_pickle=False)
    waveform = payload["data"].astype(np.float64)
    channels = [part.strip() for part in str(payload["channels"]).split(",") if part.strip()]
    if len(channels) < waveform.shape[1]:
        channels.extend(f"CH{index + 1}" for index in range(len(channels), waveform.shape[1]))
    channels = channels[: waveform.shape[1]]

    starttime = UTCDateTime(str(payload["start_time"]))
    sampling_rate = 1.0 / float(payload["dt"])
    network = str(payload["network"])
    station = str(payload["station"])
    location_code = str(payload["location_code"])

    stream = Stream()
    for column_index in range(waveform.shape[1]):
        trace = Trace(data=waveform[:, column_index])
        trace.stats.network = network
        trace.stats.station = station
        trace.stats.location = "" if location_code == "--" else location_code
        trace.stats.channel = channels[column_index]
        trace.stats.sampling_rate = sampling_rate
        trace.stats.starttime = starttime
        stream.append(trace)
    return stream


def choose_vertical_trace(stream: Stream) -> Trace:
    for trace in stream:
        if str(trace.stats.channel).endswith("Z"):
            return trace
    return stream[-1]


def format_time(timestamp: UTCDateTime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


rows = []
with REFERENCE_PATH.open(encoding="utf-8", newline="") as handle:
    references = sorted(csv.DictReader(handle), key=lambda row: row["file_name"])

for reference in references:
    file_name = reference["file_name"]
    p_idx = int(reference["p_idx"])
    s_idx = int(reference["s_idx"])
    stream = load_stream(DATA_DIR / file_name)
    vertical = choose_vertical_trace(stream)
    dt = 1.0 / float(vertical.stats.sampling_rate)

    p_arrival = vertical.stats.starttime + p_idx * dt
    s_arrival = vertical.stats.starttime + s_idx * dt

    window = vertical.data[p_idx : s_idx + 1]
    relative_peak_index = int(np.argmax(np.abs(window)))
    peak_index = p_idx + relative_peak_index
    peak_abs_scaled = round(float(np.max(np.abs(window))) * 1e10, 6)

    rows.append(
        {
            "file_name": file_name,
            "network": str(vertical.stats.network),
            "station": str(vertical.stats.station),
            "vertical_channel": str(vertical.stats.channel),
            "p_arrival_utc": format_time(p_arrival),
            "s_arrival_utc": format_time(s_arrival),
            "s_minus_p_seconds": f"{round((s_idx - p_idx) * dt, 3):.3f}",
            "vertical_peak_idx": str(peak_index),
            "vertical_peak_abs_scaled": f"{peak_abs_scaled:.6f}",
        }
    )

with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "file_name",
            "network",
            "station",
            "vertical_channel",
            "p_arrival_utc",
            "s_arrival_utc",
            "s_minus_p_seconds",
            "vertical_peak_idx",
            "vertical_peak_abs_scaled",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
