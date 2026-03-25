#!/bin/bash
set -euo pipefail

python3 <<'PY'
import pandas as pd
from obspy import UTCDateTime, read

PICK_CLUSTER_TOLERANCE = 1.2
MIN_STATIONS = 3
MIN_PICKS = 4
EPOCH = UTCDateTime(1970, 1, 1)


def format_time(value: UTCDateTime) -> str:
    return value.datetime.replace(tzinfo=None).isoformat(timespec="microseconds")


stream = read("/root/data/ridgecrest_hour.mseed")
trace_lookup = {}
for trace in stream:
    trace_lookup[trace.id] = {
        "starttime": trace.stats.starttime,
        "sampling_rate": float(trace.stats.sampling_rate),
        "network": trace.stats.network,
        "station": trace.stats.station,
        "channel": trace.stats.channel,
    }

stations = pd.read_csv("/root/data/stations_subset.csv", keep_default_na=False)
valid_station_rows = {
    (row.network, row.station, row.channel)
    for row in stations.itertuples(index=False)
}

picks = pd.read_csv("/root/data/precomputed_phase_picks.csv")
origin_proposals = []
for row in picks.itertuples(index=False):
    trace_meta = trace_lookup.get(row.trace_id)
    if trace_meta is None:
        continue

    station_key = (
        trace_meta["network"],
        trace_meta["station"],
        trace_meta["channel"],
    )
    if station_key not in valid_station_rows:
        continue

    arrival_time = trace_meta["starttime"] + (float(row.arrival_sample) / trace_meta["sampling_rate"])
    origin_time = arrival_time - float(row.origin_backshift_s)
    origin_proposals.append(
        {
            "origin_time": origin_time,
            "station": trace_meta["station"],
        }
    )

origin_proposals.sort(key=lambda item: item["origin_time"] - EPOCH)

clusters = []
for proposal in origin_proposals:
    if not clusters:
        clusters.append([proposal])
        continue

    previous = clusters[-1][-1]["origin_time"]
    if proposal["origin_time"] - previous <= PICK_CLUSTER_TOLERANCE:
        clusters[-1].append(proposal)
    else:
        clusters.append([proposal])

rows = []
for cluster in clusters:
    stations_in_cluster = {item["station"] for item in cluster}
    if len(cluster) < MIN_PICKS or len(stations_in_cluster) < MIN_STATIONS:
        continue

    timestamps = sorted(item["origin_time"] - EPOCH for item in cluster)
    mid = len(timestamps) // 2
    if len(timestamps) % 2 == 1:
        event_time = EPOCH + timestamps[mid]
    else:
        event_time = EPOCH + ((timestamps[mid - 1] + timestamps[mid]) / 2.0)

    rows.append(
        {
            "time": format_time(event_time),
            "station_count": len(stations_in_cluster),
            "phase_count": len(cluster),
        }
    )

pd.DataFrame(rows).sort_values("time").to_csv("/root/associated_events.csv", index=False)
PY
