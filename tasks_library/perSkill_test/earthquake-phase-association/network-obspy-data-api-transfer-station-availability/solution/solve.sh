#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from collections import defaultdict

from obspy import read, read_inventory


def response_complete(channel):
    response = channel.response
    if response is None or response.instrument_sensitivity is None:
        return False
    return response.instrument_sensitivity.value is not None


inventory = read_inventory("/root/data/network_inventory.xml")
stream = read("/root/data/network_window.mseed")

network = inventory.networks[0]
grouped_traces = defaultdict(list)
for trace in stream:
    grouped_traces[
        (
            trace.stats.network,
            trace.stats.station,
            trace.stats.location,
            trace.stats.channel,
        )
    ].append(trace)

station_reports = []
all_channel_reports = []

for station in sorted(network.stations, key=lambda item: item.code):
    channel_reports = []
    for channel in sorted(station.channels, key=lambda item: (item.location_code or "", item.code)):
        key = (network.code, station.code, channel.location_code or "", channel.code)
        traces = grouped_traces.get(key, [])
        coverage_seconds = sum(trace.stats.npts / trace.stats.sampling_rate for trace in traces)
        sample_rate_hz = traces[0].stats.sampling_rate if traces else channel.sample_rate
        report = {
            "trace_id": f"{network.code}.{station.code}.{channel.location_code or ''}.{channel.code}",
            "location": channel.location_code or "",
            "channel": channel.code,
            "sample_rate_hz": float(sample_rate_hz),
            "trace_count": len(traces),
            "coverage_seconds": float(coverage_seconds),
            "has_waveform_data": bool(traces),
            "response_complete": response_complete(channel),
        }
        channel_reports.append(report)
        all_channel_reports.append(report)

    station_reports.append(
        {
            "station": station.code,
            "channel_count": len(channel_reports),
            "channels_with_waveforms": sum(1 for item in channel_reports if item["has_waveform_data"]),
            "total_coverage_seconds": float(sum(item["coverage_seconds"] for item in channel_reports)),
            "channels": channel_reports,
        }
    )

result = {
    "network": network.code,
    "stations": station_reports,
    "summary": {
        "channel_count": len(all_channel_reports),
        "channels_with_waveforms": sum(1 for item in all_channel_reports if item["has_waveform_data"]),
        "channels_missing_response": sum(1 for item in all_channel_reports if not item["response_complete"]),
        "total_coverage_seconds": float(sum(item["coverage_seconds"] for item in all_channel_reports)),
    },
}

with open("/root/network_availability.json", "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
PY
