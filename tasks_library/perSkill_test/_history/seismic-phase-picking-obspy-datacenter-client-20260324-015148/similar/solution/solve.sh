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
import math
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

request_path = Path("/root/requests/waveform_requests.csv")
rows = []
with request_path.open(newline="", encoding="utf-8") as handle:
    for request in csv.DictReader(handle):
        location = "" if request["location"] == "--" else request["location"]
        stream = client.get_waveforms(
            request["network"],
            request["station"],
            location,
            request["channel"],
            UTCDateTime(request["starttime"]),
            UTCDateTime(request["endtime"]),
        )
        for trace in stream:
            data = [float(value) for value in trace.data]
            location_code = trace.stats.location or "--"
            rows.append(
                {
                    "request_id": request["request_id"],
                    "trace_id": f"{trace.stats.network}.{trace.stats.station}.{location_code}.{trace.stats.channel}",
                    "sample_count": str(len(data)),
                    "peak_abs": f"{max(abs(value) for value in data):.6f}",
                    "mean_abs": f"{sum(abs(value) for value in data) / len(data):.6f}",
                    "rms": f"{math.sqrt(sum(value * value for value in data) / len(data)):.6f}",
                }
            )

rows.sort(key=lambda row: row["request_id"])
output_path = Path("/root/similar_waveform_metrics.csv")
with output_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["request_id", "trace_id", "sample_count", "peak_abs", "mean_abs", "rms"])
    writer.writeheader()
    writer.writerows(rows)

largest = max(rows, key=lambda row: float(row["peak_abs"]))
summary = {
    "request_count": len({row["request_id"] for row in rows}),
    "trace_count": len(rows),
    "largest_peak_trace": largest["trace_id"],
    "largest_peak_value": float(largest["peak_abs"]),
}
Path("/root/similar_waveform_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY
