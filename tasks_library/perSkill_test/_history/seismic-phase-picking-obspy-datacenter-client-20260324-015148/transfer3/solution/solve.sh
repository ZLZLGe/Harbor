#!/bin/bash
set -euo pipefail

python /root/tools/seismic_archive_service.py --dataset /root/data/service_dataset.json --port 18080 >/tmp/archive.log 2>&1 &
server_pid=$!
cleanup() {
  kill "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT

python - <<'PY'
import csv
import math
import time
from datetime import timedelta
from pathlib import Path
from urllib.request import urlopen

from obspy.clients.fdsn import Client

def wait_for_service() -> None:
    for _ in range(100):
        try:
            with urlopen("http://127.0.0.1:18080/healthz", timeout=0.2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("archive service did not start")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return radius_km * (2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))

wait_for_service()
client = Client("http://127.0.0.1:18080", _discover_services=False)

rows = []
with Path("/root/requests/response_targets.csv").open(newline="", encoding="utf-8") as handle:
    for request in csv.DictReader(handle):
        catalog = client.get_events(eventid=request["event_id"])
        event = catalog[0]
        origin = event.preferred_origin() or event.origins[0]
        place = event.event_descriptions[0].text if event.event_descriptions else "unknown"

        inventory = client.get_stations(
            network=request["network"],
            channel=request["channel_glob"],
            starttime=origin.time,
            endtime=origin.time,
            level="channel",
        )

        candidates = []
        for network in inventory:
            for station in network:
                distance = haversine_km(origin.latitude, origin.longitude, station.latitude, station.longitude)
                for channel in station.channels:
                    location_code = channel.location_code or "--"
                    candidates.append(
                        (
                            distance,
                            f"{network.code}.{station.code}",
                            f"{network.code}.{station.code}.{location_code}.{channel.code}",
                        )
                    )

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        best_distance, best_station, best_channel = candidates[0]

        lead = int(request["lead_seconds"])
        lag = int(request["lag_seconds"])
        request_start = (origin.time.datetime - timedelta(seconds=lead)).strftime("%Y-%m-%dT%H:%M:%S")
        request_end = (origin.time.datetime + timedelta(seconds=lag)).strftime("%Y-%m-%dT%H:%M:%S")

        rows.append(
            {
                "event_id": request["event_id"],
                "event_place": place,
                "station_id": best_station,
                "channel_id": best_channel,
                "distance_km": f"{best_distance:.3f}",
                "request_start": request_start,
                "request_end": request_end,
            }
        )

with Path("/root/transfer3_response_plan.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["event_id", "event_place", "station_id", "channel_id", "distance_km", "request_start", "request_end"])
    writer.writeheader()
    writer.writerows(rows)
PY
