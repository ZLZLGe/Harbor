#!/bin/bash
set -euo pipefail

pip install --no-cache-dir obspy

python3 <<'PY'
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime
from obspy.core.event import Catalog, Event, Magnitude, Origin
from obspy.core.inventory import Channel, Inventory, Network, Site, Station


DATA_DIR = Path("/root/data")
WAVEFORM_DIR = DATA_DIR / "waveforms"
OUTPUT_FILE = Path("/root/arrival_windows.csv")


def isoformat_utc(time_obj: UTCDateTime) -> str:
    return time_obj.datetime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_event_definitions() -> dict[str, dict]:
    events: dict[str, dict] = {}

    with (DATA_DIR / "events.csv").open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            events[row["event_id"]] = {
                "event_id": row["event_id"],
                "origin_time": row["origin_time"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "depth_km": float(row["depth_km"]),
                "magnitude": float(row["magnitude"]),
                "magnitude_type": row["magnitude_type"],
                "review_pre_sec": float(row["review_pre_sec"]),
                "review_post_sec": float(row["review_post_sec"]),
            }

    with (DATA_DIR / "event_updates.json").open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    for row in payload["events"]:
        events[row["event_id"]] = {
            "event_id": row["event_id"],
            "origin_time": row["origin_time"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "depth_km": float(row["depth_km"]),
            "magnitude": float(row["magnitude"]),
            "magnitude_type": row["magnitude_type"],
            "review_pre_sec": float(row["review_pre_sec"]),
            "review_post_sec": float(row["review_post_sec"]),
        }

    return events


def build_catalog(event_defs: dict[str, dict]) -> Catalog:
    events: list[Event] = []
    for event_id in sorted(event_defs):
        definition = event_defs[event_id]
        origin_time = UTCDateTime(definition["origin_time"])
        event = Event(resource_id=f"smi:local/{event_id}")
        event.origins = [
            Origin(
                time=origin_time,
                latitude=definition["latitude"],
                longitude=definition["longitude"],
                depth=definition["depth_km"] * 1000.0,
            )
        ]
        event.magnitudes = [
            Magnitude(
                mag=definition["magnitude"],
                magnitude_type=definition["magnitude_type"],
            )
        ]
        events.append(event)
    return Catalog(events=events)


def load_station_definitions() -> dict[tuple[str, str, str], dict]:
    stations: dict[tuple[str, str, str], dict] = {}

    with (DATA_DIR / "stations.csv").open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (row["network"], row["station"], row["location"])
            stations[key] = {
                "network": row["network"],
                "station": row["station"],
                "location": row["location"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "elevation_m": float(row["elevation_m"]),
            }

    with (DATA_DIR / "station_updates.json").open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    for row in payload["stations"]:
        key = (row["network"], row["station"], row["location"])
        stations[key] = {
            "network": row["network"],
            "station": row["station"],
            "location": row["location"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "elevation_m": float(row["elevation_m"]),
        }

    return stations


def build_inventory(station_defs: dict[tuple[str, str, str], dict]) -> Inventory:
    networks: dict[str, Network] = {}
    for key in sorted(station_defs):
        definition = station_defs[key]
        network_code = definition["network"]
        network = networks.setdefault(network_code, Network(code=network_code, stations=[]))

        station = Station(
            code=definition["station"],
            latitude=definition["latitude"],
            longitude=definition["longitude"],
            elevation=definition["elevation_m"],
            site=Site(name=definition["station"]),
            channels=[],
        )
        network.stations.append(station)

    return Inventory(networks=list(networks.values()), source="aftershock-review-package")


def trace_from_array(data: np.ndarray, meta: dict, channels: list[str]) -> Stream:
    data = np.asarray(data, dtype=np.float32)
    if data.ndim == 1:
        data = data[:, np.newaxis]

    dt = float(meta["dt"])
    start_time = UTCDateTime(meta["start_time"])
    sampling_rate = 1.0 / dt

    traces = []
    for idx, channel in enumerate(channels):
        if idx >= data.shape[1]:
            break
        trace = Trace(data=data[:, idx].copy())
        trace.stats.network = meta["network"]
        trace.stats.station = meta["station"]
        trace.stats.location = meta["location"]
        trace.stats.channel = channel
        trace.stats.starttime = start_time
        trace.stats.sampling_rate = sampling_rate
        traces.append(trace)

    return Stream(traces=traces)


def load_npz_waveform(path: Path) -> tuple[dict, Stream]:
    payload = np.load(path, allow_pickle=False)
    meta = {
        "event_id": str(payload["event_id"]),
        "network": str(payload["network"]),
        "station": str(payload["station"]),
        "location": str(payload["location"]),
        "start_time": str(payload["start_time"]),
        "dt": float(payload["dt"]),
    }
    channels = str(payload["channels"]).split(",")
    stream = trace_from_array(payload["data"], meta, channels)
    return meta, stream


def load_json_waveform(path: Path) -> tuple[dict, Stream]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    meta = {
        "event_id": payload["event_id"],
        "network": payload["network"],
        "station": payload["station"],
        "location": payload["location"],
        "start_time": payload["start_time"],
        "dt": float(payload["dt"]),
    }
    channels = [trace_def["channel"] for trace_def in payload["traces"]]
    columns = [np.asarray(trace_def["samples"], dtype=np.float32) for trace_def in payload["traces"]]
    data = np.column_stack(columns)
    stream = trace_from_array(data, meta, channels)
    return meta, stream


def load_csv_waveform(path: Path) -> tuple[dict, Stream]:
    meta: dict[str, str] = {}
    channel_samples: dict[str, list[float]] = defaultdict(list)

    with path.open("r", encoding="utf-8", newline="") as fh:
        while True:
            position = fh.tell()
            line = fh.readline()
            if not line:
                break
            if line.startswith("# "):
                key, value = line[2:].strip().split("=", 1)
                meta[key] = value
                continue
            fh.seek(position)
            break

        reader = csv.DictReader(fh)
        for row in reader:
            channel_samples[row["channel"]].append(float(row["amplitude"]))

    ordered_channels = sorted(channel_samples)
    lengths = {len(channel_samples[channel]) for channel in ordered_channels}
    if len(lengths) != 1:
        raise ValueError(f"Inconsistent channel lengths in {path.name}")

    data = np.column_stack([np.asarray(channel_samples[channel], dtype=np.float32) for channel in ordered_channels])
    stream = trace_from_array(
        data,
        {
            "event_id": meta["event_id"],
            "network": meta["network"],
            "station": meta["station"],
            "location": meta.get("location", ""),
            "start_time": meta["start_time"],
            "dt": float(meta["dt"]),
        },
        ordered_channels,
    )
    return {
        "event_id": meta["event_id"],
        "network": meta["network"],
        "station": meta["station"],
        "location": meta.get("location", ""),
        "start_time": meta["start_time"],
        "dt": float(meta["dt"]),
    }, stream


def load_waveform(path: Path) -> tuple[dict, Stream]:
    if path.suffix == ".npz":
        return load_npz_waveform(path)
    if path.suffix == ".json":
        return load_json_waveform(path)
    if path.suffix == ".csv":
        return load_csv_waveform(path)
    raise ValueError(f"Unsupported waveform format: {path.suffix}")


def build_station_channels(inventory: Inventory, station_key: tuple[str, str, str], stream: Stream) -> None:
    for network in inventory.networks:
        if network.code != station_key[0]:
            continue
        for station in network.stations:
            if station.code != station_key[1]:
                continue
            if station.channels:
                return
            definition = next((tr for tr in stream), None)
            if definition is None:
                return
            for trace in stream:
                station.channels.append(
                    Channel(
                        code=trace.stats.channel,
                        location_code=trace.stats.location,
                        latitude=station.latitude,
                        longitude=station.longitude,
                        elevation=station.elevation,
                        depth=0.0,
                        azimuth=0.0,
                        dip=0.0,
                        sample_rate=float(trace.stats.sampling_rate),
                    )
                )
            return


def compute_rows(event_defs: dict[str, dict], station_defs: dict[tuple[str, str, str], dict], inventory: Inventory) -> list[dict]:
    rows = []

    for path in sorted(WAVEFORM_DIR.iterdir()):
        if not path.is_file():
            continue

        meta, stream = load_waveform(path)
        station_key = (meta["network"], meta["station"], meta["location"])
        event_id = meta["event_id"]

        if event_id not in event_defs:
            continue
        if station_key not in station_defs:
            continue
        if len(stream) < 2:
            continue

        sample_rates = {round(float(trace.stats.sampling_rate), 8) for trace in stream}
        if len(sample_rates) != 1:
            continue

        build_station_channels(inventory, station_key, stream)

        trace_start = max(trace.stats.starttime for trace in stream)
        trace_end = min(trace.stats.starttime + (trace.stats.npts / trace.stats.sampling_rate) for trace in stream)
        if trace_end <= trace_start:
            continue

        event_def = event_defs[event_id]
        origin_time = UTCDateTime(event_def["origin_time"])
        template_start = origin_time - event_def["review_pre_sec"]
        template_end = origin_time + event_def["review_post_sec"]
        review_start = max(trace_start, template_start)
        review_end = min(trace_end, template_end)
        if review_end <= review_start:
            continue

        coverage = sorted(trace.stats.channel for trace in stream)
        rows.append(
            {
                "event_id": event_id,
                "network": meta["network"],
                "station": meta["station"],
                "location": meta["location"],
                "waveform_file": path.name,
                "origin_time": isoformat_utc(origin_time),
                "trace_start": isoformat_utc(trace_start),
                "trace_end": isoformat_utc(trace_end),
                "review_start": isoformat_utc(review_start),
                "review_end": isoformat_utc(review_end),
                "start_offset_sec": f"{float(review_start - origin_time):.6f}",
                "end_offset_sec": f"{float(review_end - origin_time):.6f}",
                "sample_rate_hz": f"{float(stream[0].stats.sampling_rate):.6f}",
                "window_duration_sec": f"{float(review_end - review_start):.6f}",
                "channel_count": str(len(stream)),
                "channel_coverage": "|".join(coverage),
            }
        )

    rows.sort(key=lambda row: (row["event_id"], row["network"], row["station"], row["location"], row["waveform_file"]))
    return rows


def write_rows(rows: list[dict]) -> None:
    fieldnames = [
        "event_id",
        "network",
        "station",
        "location",
        "waveform_file",
        "origin_time",
        "trace_start",
        "trace_end",
        "review_start",
        "review_end",
        "start_offset_sec",
        "end_offset_sec",
        "sample_rate_hz",
        "window_duration_sec",
        "channel_count",
        "channel_coverage",
    ]
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    event_defs = load_event_definitions()
    station_defs = load_station_definitions()
    _catalog = build_catalog(event_defs)
    inventory = build_inventory(station_defs)
    rows = compute_rows(event_defs, station_defs, inventory)
    write_rows(rows)


if __name__ == "__main__":
    main()
PY
