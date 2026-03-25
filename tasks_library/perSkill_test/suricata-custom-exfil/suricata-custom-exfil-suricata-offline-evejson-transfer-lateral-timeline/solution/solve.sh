#!/bin/bash
set -euo pipefail

mkdir -p /root/answer

log_dir="$(mktemp -d /tmp/lateral-timeline.XXXXXX)"
export LOG_DIR="$log_dir"

suricata \
  --runmode single \
  -c /root/lateral-timeline/suricata.yaml \
  -S /root/lateral-timeline/lateral.rules \
  -k none \
  -r /root/lateral-timeline/ops-east-long.pcap \
  -l "$log_dir"

python3 <<'PY'
import csv
import json
import os
from pathlib import Path

eve_path = Path(os.environ["LOG_DIR"]) / "eve.json"
answer_path = Path("/root/answer/lateral-timeline.csv")
rows_by_sid = {}

for line in eve_path.read_text(errors="replace").splitlines():
    if not line.strip():
        continue
    event = json.loads(line)
    if event.get("event_type") != "alert":
        continue
    alert = event.get("alert") or {}
    signature = alert.get("signature")
    sid = alert.get("signature_id")
    if not isinstance(signature, str) or not signature.startswith("[first-wave] "):
        continue
    if not isinstance(sid, int):
        continue
    row = {
        "timestamp": event["timestamp"],
        "sid": sid,
        "src_ip": event["src_ip"],
        "dest_ip": event["dest_ip"],
        "signature": signature,
    }
    current = rows_by_sid.get(sid)
    if current is None or (row["timestamp"], row["sid"]) < (current["timestamp"], current["sid"]):
        rows_by_sid[sid] = row

ordered_rows = sorted(rows_by_sid.values(), key=lambda item: (item["timestamp"], item["sid"]))

with answer_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["timestamp", "sid", "src_ip", "dest_ip", "signature"])
    writer.writeheader()
    writer.writerows(ordered_rows)
PY
