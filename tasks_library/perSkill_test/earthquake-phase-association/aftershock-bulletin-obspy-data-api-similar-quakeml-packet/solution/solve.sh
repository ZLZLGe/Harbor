#!/bin/bash

set -euo pipefail

python3 <<'PY'
from pathlib import Path

import pandas as pd
from obspy import Catalog, UTCDateTime, read
from obspy.core.event import Event, Origin, OriginQuality

DATA_DIR = Path("/root/data")
SEGMENT_DIR = DATA_DIR / "segments"
STATIONS_CSV = DATA_DIR / "station_channels.csv"
CANDIDATES_CSV = DATA_DIR / "candidate_events.csv"
OUTPUT_XML = Path("/root/aftershock_catalog.xml")

WINDOW_BEFORE = 12
WINDOW_AFTER = 18
MIN_SUPPORT = 11


def load_archive():
    segment_paths = sorted(SEGMENT_DIR.glob("*.mseed"))
    stream = read(str(segment_paths[0]))
    for path in segment_paths[1:]:
        stream += read(str(path))
    stream.sort()
    return stream


def build_station_bundles(stations_df):
    bundles = {}
    for (network, station, location), group in stations_df.groupby(
        ["network", "station", "location"], dropna=False
    ):
        location = "" if pd.isna(location) else str(location)
        channels = set(group["channel"])
        options = []
        if {"HHE", "HHN", "HHZ"}.issubset(channels):
            options.append(("HHE", "HHN", "HHZ"))
        if {"HNE", "HNN", "HNZ"}.issubset(channels):
            options.append(("HNE", "HNN", "HNZ"))
        if options:
            bundles[(network, station, location)] = options
    return bundles


def channel_covers(stream, network, station, location, channel, start, end):
    selected = sorted(
        stream.select(
            network=network,
            station=station,
            location=location,
            channel=channel,
        ),
        key=lambda trace: trace.stats.starttime,
    )
    if not selected:
        return False

    coverage_end = None
    for trace in selected:
        trace_start = trace.stats.starttime
        trace_end = trace.stats.endtime
        tolerance = trace.stats.delta

        if trace_end < start:
            continue
        if coverage_end is None:
            if trace_start > start + tolerance:
                return False
            coverage_end = trace_end
        elif trace_start > coverage_end + tolerance:
            return False
        elif trace_end > coverage_end:
            coverage_end = trace_end

        if coverage_end >= end:
            return True

    return False


def station_supports(stream, station_key, bundle_options, start, end):
    network, station, location = station_key
    for bundle in bundle_options:
        if all(
            channel_covers(stream, network, station, location, channel, start, end)
            for channel in bundle
        ):
            return True
    return False


archive = load_archive()
stations_df = pd.read_csv(STATIONS_CSV, na_filter=False)
candidates_df = pd.read_csv(CANDIDATES_CSV)
station_bundles = build_station_bundles(stations_df)

catalog = Catalog()
for row in candidates_df.itertuples(index=False):
    origin_time = UTCDateTime(row.origin_time)
    start = origin_time - WINDOW_BEFORE
    end = origin_time + WINDOW_AFTER
    support_count = sum(
        1
        for station_key, bundle_options in station_bundles.items()
        if station_supports(archive, station_key, bundle_options, start, end)
    )
    if support_count < MIN_SUPPORT:
        continue

    event = Event()
    event.origins = [
        Origin(
            time=origin_time,
            quality=OriginQuality(used_station_count=support_count),
        )
    ]
    catalog.events.append(event)

catalog.events.sort(key=lambda event: event.origins[0].time)
catalog.write(str(OUTPUT_XML), format="QUAKEML")
PY
