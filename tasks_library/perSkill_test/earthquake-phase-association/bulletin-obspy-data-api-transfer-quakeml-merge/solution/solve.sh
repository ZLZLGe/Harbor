#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import os
import re
from collections import defaultdict

from obspy import read_events
from obspy.core.utcdatetime import UTCDateTime

INPUT_ROOT = "/root/data/quakeml_fragments"
OUTPUT_PATH = "/root/regional_bulletin.csv"


def normalize_event_id(resource_id) -> str:
    text = str(resource_id)
    token = text.rstrip("/").split("/")[-1]
    return re.sub(r"-rev\d+$", "", token)


def choose_origin(event):
    preferred = event.preferred_origin()
    if preferred is not None:
        return preferred
    origins = [origin for origin in event.origins if origin.time is not None]
    if not origins:
        raise ValueError(f"event {event.resource_id} has no origin with time")
    return min(origins, key=lambda origin: origin.time)


def choose_magnitude(event):
    preferred = event.preferred_magnitude()
    if preferred is not None:
        return preferred
    return event.magnitudes[0] if event.magnitudes else None


def update_time(event, origin) -> UTCDateTime:
    origin_creation = getattr(getattr(origin, "creation_info", None), "creation_time", None)
    if origin_creation is not None:
        return origin_creation
    event_creation = getattr(getattr(event, "creation_info", None), "creation_time", None)
    if event_creation is not None:
        return event_creation
    return origin.time


def as_float(value):
    return None if value is None else float(value)


rows_by_key = {}
counts = defaultdict(int)

for root, _, files in os.walk(INPUT_ROOT):
    for name in sorted(files):
        if not name.endswith(".xml"):
            continue
        catalog = read_events(os.path.join(root, name))
        for event in catalog:
            origin = choose_origin(event)
            magnitude = choose_magnitude(event)
            event_id = normalize_event_id(event.resource_id)
            dedupe_second = origin.time.strftime("%Y-%m-%dT%H:%M:%S")
            key = (event_id, dedupe_second)
            counts[key] += 1

            row = {
                "event_id": event_id,
                "time": origin.time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "latitude": as_float(origin.latitude),
                "longitude": as_float(origin.longitude),
                "depth_km": None if origin.depth is None else float(origin.depth) / 1000.0,
                "magnitude": None if magnitude is None or magnitude.mag is None else float(magnitude.mag),
                "magnitude_type": "" if magnitude is None or magnitude.magnitude_type is None else str(magnitude.magnitude_type),
                "_updated_at": update_time(event, origin),
            }

            current = rows_by_key.get(key)
            if current is None:
                rows_by_key[key] = row
                continue

            current_mag = current["magnitude"]
            candidate_mag = row["magnitude"]
            candidate_is_newer = row["_updated_at"] > current["_updated_at"]
            same_update = row["_updated_at"] == current["_updated_at"]
            better_magnitude = (
                candidate_mag is not None
                and (current_mag is None or candidate_mag > current_mag)
            )

            if candidate_is_newer or (same_update and better_magnitude):
                rows_by_key[key] = row

final_rows = []
for key, row in rows_by_key.items():
    output = {
        "event_id": row["event_id"],
        "time": row["time"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "depth_km": row["depth_km"],
        "magnitude": row["magnitude"],
        "magnitude_type": row["magnitude_type"],
        "source_count": counts[key],
    }
    final_rows.append(output)

final_rows.sort(key=lambda item: (item["time"], item["event_id"]))

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "event_id",
            "time",
            "latitude",
            "longitude",
            "depth_km",
            "magnitude",
            "magnitude_type",
            "source_count",
        ],
    )
    writer.writeheader()
    writer.writerows(final_rows)
PY
