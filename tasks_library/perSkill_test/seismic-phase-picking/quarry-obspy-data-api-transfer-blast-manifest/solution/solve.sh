#!/bin/bash

set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime, read_events, read_inventory


DATA_DIR = Path("/root/data")
OUTPUT_FILE = Path("/root/blast_station_manifest.json")


def format_time(value: UTCDateTime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def suffix_matches(public_id: str, suffix: str) -> bool:
    return public_id == suffix or public_id.endswith("/" + suffix)


def build_event_lookup(catalog):
    lookup = {}
    for event in catalog:
        public_id = str(event.resource_id)
        key = public_id.rsplit("/", 1)[-1]
        lookup.setdefault(key, []).append(event)
    return lookup


def build_station_lookup(inventory):
    lookup = {}
    for network in inventory:
        for station in network:
            channels_by_location = {}
            for channel in station.channels:
                channels_by_location.setdefault(channel.location_code, {})[channel.code] = channel
            for location_code, channel_map in channels_by_location.items():
                lookup[(network.code, station.code, location_code)] = {
                    "station": station,
                    "channels": channel_map,
                }
    return lookup


def load_snippet(path: Path):
    bundle = np.load(path, allow_pickle=False)
    event_id = str(bundle["event_id"])
    network = str(bundle["network"])
    station = str(bundle["station"])
    location = str(bundle["location"])
    dt = float(bundle["dt"])
    channels = [str(value) for value in bundle["channels"].tolist()]
    start_times = [UTCDateTime(str(value)) for value in bundle["start_times"].tolist()]
    sample_counts = [int(value) for value in bundle["sample_counts"].tolist()]
    data = bundle["data"]

    sampling_rate = 1.0 / dt
    stream = Stream()
    for index, channel in enumerate(channels):
        npts = sample_counts[index]
        samples = np.asarray(data[:npts, index], dtype=np.float32)
        trace = Trace(data=samples)
        trace.stats.network = network
        trace.stats.station = station
        trace.stats.location = location
        trace.stats.channel = channel
        trace.stats.starttime = start_times[index]
        trace.stats.sampling_rate = sampling_rate
        stream.append(trace)

    return {
        "event_id": event_id,
        "network": network,
        "station": station,
        "location": location,
        "sampling_rate": sampling_rate,
        "stream": stream,
    }


catalog = read_events(str(DATA_DIR / "events" / "quarry_blasts.xml"))
inventory = read_inventory(str(DATA_DIR / "stations" / "quarry_inventory.xml"))
event_lookup = build_event_lookup(catalog)
station_lookup = build_station_lookup(inventory)

records = []
for waveform_path in sorted((DATA_DIR / "waveforms").glob("*.npz")):
    snippet = load_snippet(waveform_path)
    stream = snippet["stream"]

    matched_events = event_lookup.get(snippet["event_id"], [])
    if len(matched_events) != 1:
        continue
    event = matched_events[0]

    station_key = (snippet["network"], snippet["station"], snippet["location"])
    station_entry = station_lookup.get(station_key)
    if station_entry is None:
        continue

    if len(stream) < 2:
        continue

    sample_rates = {round(trace.stats.sampling_rate, 12) for trace in stream}
    if len(sample_rates) != 1:
        continue

    channel_map = station_entry["channels"]
    if any(trace.stats.channel not in channel_map for trace in stream):
        continue

    sampling_rate = stream[0].stats.sampling_rate
    inventory_rates = {round(channel_map[trace.stats.channel].sample_rate, 12) for trace in stream}
    if inventory_rates != {round(sampling_rate, 12)}:
        continue

    origin = event.preferred_origin() or event.origins[0]
    magnitude = event.preferred_magnitude() or (event.magnitudes[0] if event.magnitudes else None)

    trace_start = max(trace.stats.starttime for trace in stream)
    trace_end = min(trace.stats.starttime + trace.stats.npts / trace.stats.sampling_rate for trace in stream)
    if trace_end <= trace_start:
        continue
    if not (trace_start <= origin.time < trace_end):
        continue

    station = station_entry["station"]
    records.append(
        {
            "event_id": snippet["event_id"],
            "event_time": format_time(origin.time),
            "event_latitude": float(origin.latitude),
            "event_longitude": float(origin.longitude),
            "event_depth_m": float(origin.depth),
            "event_magnitude": None if magnitude is None else float(magnitude.mag),
            "station_network": snippet["network"],
            "station_code": snippet["station"],
            "station_location": snippet["location"],
            "station_latitude": float(station.latitude),
            "station_longitude": float(station.longitude),
            "station_elevation_m": float(station.elevation),
            "waveform_file": waveform_path.name,
            "trace_start": format_time(trace_start),
            "trace_start_offset_sec": float(trace_start - origin.time),
            "trace_duration_sec": float(trace_end - trace_start),
            "sample_rate_hz": float(sampling_rate),
            "channel_set": sorted(trace.stats.channel for trace in stream),
        }
    )

records.sort(
    key=lambda item: (
        item["event_time"],
        item["station_network"],
        item["station_code"],
        item["station_location"],
        item["waveform_file"],
    )
)

manifest = {
    "quarry_name": "Basalt Ridge Quarry",
    "record_count": len(records),
    "records": records,
}

OUTPUT_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY
