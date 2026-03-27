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

rows = []
with Path("/root/requests/station_queries.csv").open(newline="", encoding="utf-8") as handle:
    for request in csv.DictReader(handle):
        inventory = client.get_stations(
            network=request["network"],
            station=request["station"],
            channel=request["channel"],
            starttime=UTCDateTime(request["starttime"]),
            endtime=UTCDateTime(request["endtime"]),
            level="channel",
        )
        for network in inventory:
            for station in network:
                station_id = f"{network.code}.{station.code}"
                for channel in station.channels:
                    location_code = channel.location_code or "--"
                    rows.append(
                        {
                            "request_id": request["request_id"],
                            "station_id": station_id,
                            "channel_id": f"{network.code}.{station.code}.{location_code}.{channel.code}",
                            "sample_rate_hz": f"{float(channel.sample_rate):.1f}",
                            "start_date": channel.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                            "end_date": channel.end_date.strftime("%Y-%m-%dT%H:%M:%S") if channel.end_date else "open",
                        }
                    )

rows.sort(key=lambda row: (row["request_id"], row["channel_id"]))
with Path("/root/transfer1_station_channel_audit.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["request_id", "station_id", "channel_id", "sample_rate_hz", "start_date", "end_date"])
    writer.writeheader()
    writer.writerows(rows)
PY
