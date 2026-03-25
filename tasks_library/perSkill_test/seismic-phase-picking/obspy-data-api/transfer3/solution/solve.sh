#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime

DATA_DIR = Path("/root/data")
REQUEST_PATH = DATA_DIR / "window_requests.json"
OUTPUT_PATH = Path("/root/transfer3_window_manifest.json")


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
        trace.stats.starttime = UTCDateTime(str(payload["start_time"]))
        stream.append(trace)
    return stream


requests = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
windows = []
for request in requests:
    payload = load_payload(DATA_DIR / request["file_name"])
    stream = load_stream(payload)
    waveform = np.stack([trace.data for trace in stream], axis=1)
    sampling_rate = float(stream[0].stats.sampling_rate)
    starttime = stream[0].stats.starttime

    start_idx = int(round((UTCDateTime(request["window_start_utc"]) - starttime) * sampling_rate))
    end_idx = int(round((UTCDateTime(request["window_end_utc"]) - starttime) * sampling_rate))
    start_idx = max(0, min(start_idx, waveform.shape[0]))
    end_idx = max(0, min(end_idx, waveform.shape[0]))
    if waveform.shape[0] > 0 and end_idx <= start_idx:
        end_idx = min(waveform.shape[0], start_idx + 1)

    window = waveform[start_idx:end_idx, :]
    peak_by_channel = np.max(np.abs(window), axis=0)
    peak_channel_index = int(np.argmax(peak_by_channel))
    peak_channel_window = np.abs(window[:, peak_channel_index])
    peak_offset = int(np.argmax(peak_channel_window))

    windows.append(
        {
            "file_name": request["file_name"],
            "window_start_utc": request["window_start_utc"],
            "window_end_utc": request["window_end_utc"],
            "start_idx": start_idx,
            "end_idx": end_idx,
            "sample_count": int(end_idx - start_idx),
            "channel_codes": [str(trace.stats.channel) for trace in stream],
            "peak_channel": str(stream[peak_channel_index].stats.channel),
            "peak_offset_samples": peak_offset,
            "window_duration_seconds": round((end_idx - start_idx) / sampling_rate, 3),
            "window_peak_abs_scaled": round(float(peak_channel_window[peak_offset]) * 1e10, 6),
            "window_mean_abs_scaled": round(float(np.mean(peak_channel_window)) * 1e10, 6),
        }
    )

OUTPUT_PATH.write_text(
    json.dumps({"requests_processed": len(windows), "windows": windows}, indent=2),
    encoding="utf-8",
)
PY
