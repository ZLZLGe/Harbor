import json
from pathlib import Path

import numpy as np
import pytest
from obspy import Stream, Trace, UTCDateTime, read_events, read_inventory


OUTPUT_FILE = Path("/root/blast_station_manifest.json")
DATA_DIR = Path("/root/data")
EXPECTED_RECORD_KEYS = [
    "event_id",
    "event_time",
    "event_latitude",
    "event_longitude",
    "event_depth_m",
    "event_magnitude",
    "station_network",
    "station_code",
    "station_location",
    "station_latitude",
    "station_longitude",
    "station_elevation_m",
    "waveform_file",
    "trace_start",
    "trace_start_offset_sec",
    "trace_duration_sec",
    "sample_rate_hz",
    "channel_set",
]


def format_time(value: UTCDateTime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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
    channels = [str(value) for value in bundle["channels"].tolist()]
    start_times = [UTCDateTime(str(value)) for value in bundle["start_times"].tolist()]
    sample_counts = [int(value) for value in bundle["sample_counts"].tolist()]
    sampling_rate = 1.0 / float(bundle["dt"])
    data = bundle["data"]

    stream = Stream()
    for index, channel in enumerate(channels):
        npts = sample_counts[index]
        trace = Trace(data=np.asarray(data[:npts, index], dtype=np.float32))
        trace.stats.network = str(bundle["network"])
        trace.stats.station = str(bundle["station"])
        trace.stats.location = str(bundle["location"])
        trace.stats.channel = channel
        trace.stats.starttime = start_times[index]
        trace.stats.sampling_rate = sampling_rate
        stream.append(trace)

    return {
        "event_id": str(bundle["event_id"]),
        "network": str(bundle["network"]),
        "station": str(bundle["station"]),
        "location": str(bundle["location"]),
        "stream": stream,
        "sampling_rate": sampling_rate,
    }


def compute_expected_manifest():
    catalog = read_events(str(DATA_DIR / "events" / "quarry_blasts.xml"))
    inventory = read_inventory(str(DATA_DIR / "stations" / "quarry_inventory.xml"))

    event_lookup = {}
    for event in catalog:
        key = str(event.resource_id).rsplit("/", 1)[-1]
        event_lookup.setdefault(key, []).append(event)

    station_lookup = build_station_lookup(inventory)

    records = []
    for waveform_path in sorted((DATA_DIR / "waveforms").glob("*.npz")):
        snippet = load_snippet(waveform_path)
        stream = snippet["stream"]
        matched_events = event_lookup.get(snippet["event_id"], [])
        if len(matched_events) != 1:
            continue
        station_entry = station_lookup.get(
            (snippet["network"], snippet["station"], snippet["location"])
        )
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

        event = matched_events[0]
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
    return {
        "quarry_name": "Basalt Ridge Quarry",
        "record_count": len(records),
        "records": records,
    }


@pytest.fixture(scope="module")
def actual_manifest():
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Missing output file: {OUTPUT_FILE}")
    with OUTPUT_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def expected_manifest():
    return compute_expected_manifest()


def test_top_level_structure(actual_manifest, expected_manifest):
    assert list(actual_manifest.keys()) == ["quarry_name", "record_count", "records"]
    assert actual_manifest["quarry_name"] == expected_manifest["quarry_name"]
    assert actual_manifest["record_count"] == 5
    assert actual_manifest["record_count"] == expected_manifest["record_count"]
    assert len(actual_manifest["records"]) == expected_manifest["record_count"]


@pytest.mark.parametrize("index", range(5))
def test_records_match(index, actual_manifest, expected_manifest):
    actual = actual_manifest["records"][index]
    expected = expected_manifest["records"][index]

    assert list(actual.keys()) == EXPECTED_RECORD_KEYS

    for key in [
        "event_id",
        "event_time",
        "station_network",
        "station_code",
        "station_location",
        "waveform_file",
        "channel_set",
    ]:
        assert actual[key] == expected[key]

    for key in [
        "event_latitude",
        "event_longitude",
        "event_depth_m",
        "station_latitude",
        "station_longitude",
        "station_elevation_m",
        "trace_start_offset_sec",
        "trace_duration_sec",
        "sample_rate_hz",
    ]:
        assert float(actual[key]) == pytest.approx(expected[key], abs=1e-6)

    if expected["event_magnitude"] is None:
        assert actual["event_magnitude"] is None
    else:
        assert float(actual["event_magnitude"]) == pytest.approx(expected["event_magnitude"], abs=1e-6)


def test_invalid_snippets_are_excluded(actual_manifest):
    seen = {record["waveform_file"] for record in actual_manifest["records"]}
    assert "blast_alpha_late_window.npz" not in seen
    assert "blast_beta_bad_rate.npz" not in seen
    assert "blast_missing_event.npz" not in seen
    assert "blast_unknown_station.npz" not in seen


def test_records_are_sorted(actual_manifest):
    ordering = [
        (
            record["event_time"],
            record["station_network"],
            record["station_code"],
            record["station_location"],
            record["waveform_file"],
        )
        for record in actual_manifest["records"]
    ]
    assert ordering == sorted(ordering)
