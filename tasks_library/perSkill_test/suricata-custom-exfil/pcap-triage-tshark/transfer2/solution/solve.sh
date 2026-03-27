#!/bin/bash
set -euo pipefail

python3 <<'PY'
from collections import defaultdict
from pathlib import Path

from pcap_http_utils import parse_form_body, parse_query_params, read_http_requests


pcap_path = Path("/root/pcaps/transfer2_lab_uploads.pcap")
output_path = Path("/root/transfer2_lab_upload_summary.md")

accepted = []
rejected_count = 0

for request in read_http_requests(pcap_path):
    if request.method != "PUT" or request.path != "/lab/v2/upload":
        continue
    query = parse_query_params(request.uri)
    form = parse_form_body(request.body_text)
    entry = {
        "frame_number": request.frame_number,
        "station": query["station"],
        "specimen": query["specimen"],
        "bytes": int(form["bytes"]),
        "status": form["status"],
    }
    if entry["status"] == "accepted":
        accepted.append(entry)
    elif entry["status"] == "rejected":
        rejected_count += 1

station_totals = defaultdict(lambda: {"count": 0, "bytes": 0})
for entry in accepted:
    station_totals[entry["station"]]["count"] += 1
    station_totals[entry["station"]]["bytes"] += entry["bytes"]

largest = min(accepted, key=lambda item: (-item["bytes"], item["frame_number"]))

lines = [
    "# Lab Upload Summary",
    f"accepted_requests: {len(accepted)}",
    f"rejected_requests: {rejected_count}",
    "",
    "## Station Totals",
]
for station in sorted(station_totals):
    lines.append(f"- {station}: {station_totals[station]['count']} accepted, {station_totals[station]['bytes']} bytes")
lines.extend(
    [
        "",
        "## Largest Accepted Upload",
        f"frame_number: {largest['frame_number']}",
        f"station: {largest['station']}",
        f"specimen: {largest['specimen']}",
        f"bytes: {largest['bytes']}",
    ]
)

output_path.write_text("\n".join(lines) + "\n")
PY
