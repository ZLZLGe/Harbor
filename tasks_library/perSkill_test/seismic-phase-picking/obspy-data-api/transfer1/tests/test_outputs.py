import json
from collections import Counter
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime

DATA_DIR = Path("/root/data")
OUTPUT_PATH = Path("/root/transfer1_waveform_catalog.json")


def load_payload(npz_path: Path):
    return np.load(npz_path, allow_pickle=False)


def load_stream(payload) -> Stream:
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


def format_time(timestamp: UTCDateTime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def build_expected():
    file_entries = []
    for npz_path in sorted(DATA_DIR.glob("*.npz")):
        payload = load_payload(npz_path)
        stream = load_stream(payload)
        max_abs_by_trace = [float(np.max(np.abs(trace.data))) for trace in stream]
        peak_index = int(np.argmax(max_abs_by_trace))
        first_trace = stream[0]
        duration_seconds = round(float(first_trace.stats.endtime - first_trace.stats.starttime), 3)

        file_entries.append(
            {
                "file_name": npz_path.name,
                "network": str(first_trace.stats.network),
                "station": str(first_trace.stats.station),
                "location_code": str(payload["location_code"]),
                "channel_codes": [str(trace.stats.channel) for trace in stream],
                "trace_count": len(stream),
                "sample_rate_hz": round(float(first_trace.stats.sampling_rate), 3),
                "duration_seconds": duration_seconds,
                "start_utc": format_time(first_trace.stats.starttime),
                "end_utc": format_time(first_trace.stats.endtime),
                "event_time_utc": format_time(UTCDateTime(str(payload["event_time"]))),
                "distance_km": round(float(payload["distance_km"]), 1),
                "event_magnitude": round(float(payload["event_magnitude"]), 2),
                "peak_component": str(stream[peak_index].stats.channel),
                "peak_abs_scaled": round(max_abs_by_trace[peak_index] * 1e10, 6),
                "mean_snr": round(float(np.mean(payload["snr"])), 4),
            }
        )

    network_counts = Counter(entry["network"] for entry in file_entries)
    earliest_start = min(UTCDateTime(entry["start_utc"]) for entry in file_entries)
    latest_end = max(UTCDateTime(entry["end_utc"]) for entry in file_entries)
    summary = {
        "total_files": len(file_entries),
        "network_counts": {key: network_counts[key] for key in sorted(network_counts)},
        "earliest_start_utc": format_time(earliest_start),
        "latest_end_utc": format_time(latest_end),
        "mean_duration_seconds": round(
            sum(entry["duration_seconds"] for entry in file_entries) / len(file_entries),
            3,
        ),
        "max_distance_km": round(max(entry["distance_km"] for entry in file_entries), 1),
    }
    return {"summary": summary, "files": file_entries}


def main():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    actual = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = build_expected()
    assert actual == expected, "catalog JSON does not match expected waveform metadata"


if __name__ == "__main__":
    main()
