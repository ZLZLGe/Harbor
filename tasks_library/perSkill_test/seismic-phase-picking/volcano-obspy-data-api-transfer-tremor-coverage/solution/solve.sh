#!/bin/bash
set -euo pipefail

python -m pip install --no-cache-dir numpy==1.26.4 obspy==1.4.1

python - <<'PY'
import json
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime


DATA_DIR = Path("/root/data")
REGISTRY_PATH = DATA_DIR / "station_registry.json"
FRAGMENTS_DIR = DATA_DIR / "fragments"
OUTPUT_PATH = Path("/root/volcano_gap_report.json")


def format_time(value: UTCDateTime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def trace_end(trace: Trace) -> UTCDateTime:
    return trace.stats.starttime + trace.stats.npts / trace.stats.sampling_rate


def clip_intervals(intervals, audit_start, audit_end):
    clipped = []
    for start, end in intervals:
        start = max(start, audit_start)
        end = min(end, audit_end)
        if end > start:
            clipped.append((start, end))
    return clipped


def merge_intervals(intervals, tolerance=1e-6):
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda item: item[0])
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        current = merged[-1]
        if float(start - current[1]) <= tolerance:
            if end > current[1]:
                current[1] = end
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def intersect_two(left, right):
    result = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if end > start:
            result.append((start, end))
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return result


def intersect_many(interval_lists):
    if not interval_lists:
        return []
    result = interval_lists[0]
    for other in interval_lists[1:]:
        result = intersect_two(result, other)
        if not result:
            break
    return result


def hourly_coverage(intervals, audit_start):
    values = []
    for hour in range(24):
        hour_start = audit_start + hour * 3600
        hour_end = hour_start + 3600
        covered = 0.0
        for start, end in intervals:
            overlap_start = max(start, hour_start)
            overlap_end = min(end, hour_end)
            if overlap_end > overlap_start:
                covered += float(overlap_end - overlap_start)
        values.append(float(covered))
    return values


def first_gap(intervals, audit_start, audit_end):
    cursor = audit_start
    for start, end in intervals:
        if start > cursor:
            return {
                "start": format_time(cursor),
                "end": format_time(start),
                "duration_sec": float(start - cursor),
            }
        if end > cursor:
            cursor = end
    if cursor < audit_end:
        return {
            "start": format_time(cursor),
            "end": format_time(audit_end),
            "duration_sec": float(audit_end - cursor),
        }
    return None


with REGISTRY_PATH.open("r", encoding="utf-8") as fh:
    registry = json.load(fh)

audit_start = UTCDateTime(registry["audit_window_start"])
audit_end = UTCDateTime(registry["audit_window_end"])

stations = sorted(
    registry["stations"],
    key=lambda item: (item["network"], item["station"], item.get("location", "")),
)

station_lookup = {
    (item["network"], item["station"], item.get("location", "")): item
    for item in stations
}

streams = {key: Stream() for key in station_lookup}

for fragment_path in sorted(FRAGMENTS_DIR.glob("*.npz")):
    raw = np.load(fragment_path, allow_pickle=False)
    key = (str(raw["network"]), str(raw["station"]), str(raw["location"]))
    station_meta = station_lookup.get(key)
    if station_meta is None:
        continue

    channels = [str(channel) for channel in np.atleast_1d(raw["channels"])]
    data = raw["data"]
    dt = float(raw["dt"])
    starttime = UTCDateTime(str(raw["start_time"]))
    sample_rate = 1.0 / dt
    expected = set(station_meta["expected_channels"])

    for index, channel in enumerate(channels):
        if channel not in expected:
            continue
        trace = Trace(data=np.asarray(data[:, index], dtype=np.float32))
        trace.stats.network = key[0]
        trace.stats.station = key[1]
        trace.stats.location = key[2]
        trace.stats.channel = channel
        trace.stats.starttime = starttime
        trace.stats.sampling_rate = sample_rate
        streams[key].append(trace)


report_stations = []
for station_meta in stations:
    key = (station_meta["network"], station_meta["station"], station_meta.get("location", ""))
    stream = streams[key]
    expected_channels = list(station_meta["expected_channels"])

    merged_by_channel = {}
    interval_lists = []
    for channel in expected_channels:
        traces = [trace for trace in stream if trace.stats.channel == channel]
        intervals = [(trace.stats.starttime, trace_end(trace)) for trace in traces]
        merged = clip_intervals(merge_intervals(intervals), audit_start, audit_end)
        merged_by_channel[channel] = merged
        interval_lists.append(merged)

    if any(len(intervals) == 0 for intervals in interval_lists):
        coverage = []
    else:
        coverage = intersect_many(interval_lists)

    coverage_entries = [
        {
            "start": format_time(start),
            "end": format_time(end),
            "duration_sec": float(end - start),
        }
        for start, end in coverage
    ]

    total_covered = float(sum(entry["duration_sec"] for entry in coverage_entries))
    report_stations.append(
        {
            "network": station_meta["network"],
            "station": station_meta["station"],
            "location": station_meta.get("location", ""),
            "station_name": station_meta["station_name"],
            "volcano_name": station_meta["volcano_name"],
            "expected_channels": expected_channels,
            "merged_channel_interval_counts": {
                channel: len(merged_by_channel[channel]) for channel in expected_channels
            },
            "coverage_interval_count": len(coverage_entries),
            "coverage_intervals": coverage_entries,
            "hourly_coverage_seconds": hourly_coverage(coverage, audit_start),
            "total_covered_seconds": total_covered,
            "first_missing_interval": first_gap(coverage, audit_start, audit_end),
        }
    )

payload = {
    "audit_window_start": format_time(audit_start),
    "audit_window_end": format_time(audit_end),
    "station_count": len(report_stations),
    "stations": report_stations,
}

OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
