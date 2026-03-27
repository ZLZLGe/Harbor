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
import json
import time
from pathlib import Path
from urllib.request import urlopen

from obspy import UTCDateTime
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

wait_for_service()
client = Client("http://127.0.0.1:18080", _discover_services=False)

payload = []
with Path("/root/requests/event_windows.csv").open(newline="", encoding="utf-8") as handle:
    for request in csv.DictReader(handle):
        catalog = client.get_events(
            starttime=UTCDateTime(request["starttime"]),
            endtime=UTCDateTime(request["endtime"]),
            minmagnitude=float(request["minmagnitude"]),
        )
        events = []
        for event in catalog:
            origin = event.preferred_origin() or event.origins[0]
            magnitude = event.preferred_magnitude() or event.magnitudes[0]
            place = event.event_descriptions[0].text if event.event_descriptions else "unknown"
            events.append(
                {
                    "event_id": str(event.resource_id).rsplit("/", 1)[-1],
                    "time": origin.time,
                    "depth_km": float(origin.depth) / 1000.0,
                    "magnitude": float(magnitude.mag),
                    "place": place,
                }
            )

        events.sort(key=lambda item: item["time"])
        largest = max(events, key=lambda item: item["magnitude"])
        payload.append(
            {
                "request_id": request["request_id"],
                "event_count": len(events),
                "event_ids": [item["event_id"] for item in events],
                "max_magnitude": max(item["magnitude"] for item in events),
                "mean_depth_km": round(sum(item["depth_km"] for item in events) / len(events), 3),
                "largest_event_place": largest["place"],
            }
        )

Path("/root/transfer2_event_digest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
