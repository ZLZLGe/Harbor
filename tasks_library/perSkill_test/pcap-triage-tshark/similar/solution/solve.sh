#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

from pcap_http_utils import parse_form_body, read_http_requests


pcap_path = Path("/root/pcaps/similar_telemetry.pcap")
output_path = Path("/root/similar_request_audit.csv")

rows = []
for request in read_http_requests(pcap_path):
    if request.path != "/telemetry/v2/report":
        continue

    form = parse_form_body(request.body_text)
    tlm_mode = request.headers.get("x-tlm-mode", "").strip().lower()
    blob_length = len(form.get("blob", ""))
    sig_length = len(form.get("sig", ""))
    is_candidate = (
        request.method == "POST"
        and tlm_mode == "exfil"
        and blob_length >= 80
        and sig_length == 64
    )
    rows.append(
        {
            "frame_number": str(request.frame_number),
            "src_ip": request.src_ip,
            "src_port": str(request.src_port),
            "method": request.method,
            "uri": request.uri,
            "tlm_mode": tlm_mode,
            "blob_length": str(blob_length),
            "sig_length": str(sig_length),
            "is_exfil_candidate": "true" if is_candidate else "false",
        }
    )

with output_path.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "frame_number",
            "src_ip",
            "src_port",
            "method",
            "uri",
            "tlm_mode",
            "blob_length",
            "sig_length",
            "is_exfil_candidate",
        ],
    )
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda item: int(item["frame_number"])))
PY
