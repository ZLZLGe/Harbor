#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

from obspy import Stream, UTCDateTime, read

WAVEFORM_PATH = "/root/data/survey_line_12_continuous.mseed"
ROSTER_PATH = "/root/data/receiver_roster.csv"
SCHEDULE_PATH = "/root/data/shot_schedule.csv"
OUTPUT_PATH = "/root/shot_window_summary.csv"
PRE_WINDOW_SECONDS = 3.0
POST_WINDOW_SECONDS = 7.0


def format_time(value: UTCDateTime) -> str:
    return value.datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")


def trace_key(trace) -> tuple[str, str, str, str]:
    return (
        trace.stats.network,
        trace.stats.station,
        trace.stats.location,
        trace.stats.channel,
    )


def load_allowed_receivers() -> set[tuple[str, str, str, str]]:
    allowed = set()
    with open(ROSTER_PATH, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["enabled"] == "1":
                allowed.add((row["network"], row["station"], row["location"], row["channel"]))
    return allowed


def format_sample_rates(traces) -> str:
    if not traces:
        return ""
    rates = sorted({float(trace.stats.sampling_rate) for trace in traces})
    return "|".join(f"{rate:.1f}" for rate in rates)


allowed = load_allowed_receivers()
stream = read(WAVEFORM_PATH)
filtered = Stream(traces=[trace for trace in stream if trace_key(trace) in allowed])

rows = []
with open(SCHEDULE_PATH, newline="", encoding="utf-8") as handle:
    for shot in csv.DictReader(handle):
        shot_time = UTCDateTime(shot["shot_time"])
        window_start = shot_time - PRE_WINDOW_SECONDS
        window_end = shot_time + POST_WINDOW_SECONDS
        windowed = filtered.copy().slice(starttime=window_start, endtime=window_end)
        counted = [trace for trace in windowed if trace.stats.npts > 0]
        rows.append(
            {
                "shot_id": shot["shot_id"],
                "line_name": shot["line_name"],
                "shot_time": format_time(shot_time),
                "window_start": format_time(window_start),
                "window_end": format_time(window_end),
                "trace_count": len(counted),
                "station_count": len({trace.stats.station for trace in counted}),
                "sample_rates_hz": format_sample_rates(counted),
                "total_samples": sum(trace.stats.npts for trace in counted),
            }
        )

rows.sort(key=lambda row: (row["shot_time"], row["shot_id"]))

fieldnames = [
    "shot_id",
    "line_name",
    "shot_time",
    "window_start",
    "window_end",
    "trace_count",
    "station_count",
    "sample_rates_hz",
    "total_samples",
]

with Path(OUTPUT_PATH).open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
