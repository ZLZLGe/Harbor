#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
from pathlib import Path

ROOT = Path("/root")

manifest = json.loads((ROOT / "patrol_manifest.json").read_text(encoding="utf-8"))
sample_count = int(manifest["sample_count"])
sample_origin_ms = int(manifest["sample_origin_ms"])
sample_period_ms = int(manifest["sample_period_ms"])

events = []
with open(ROOT / "robot_event_log.csv", "r", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        events.append((row["event"], int(row["start_ms"]), int(row["end_ms"])))

per_sample = []
for i in range(sample_count):
    timestamp_ms = sample_origin_ms + i * sample_period_ms
    active = sorted({event for event, start_ms, end_ms in events if start_ms <= timestamp_ms < end_ms})
    per_sample.append(active or ["clear"])

windows = {}
start = 0
current = per_sample[0]

for i in range(1, sample_count + 1):
    if i == sample_count or per_sample[i] != current:
        windows[f"{start}->{i}"] = current
        if i < sample_count:
            start = i
            current = per_sample[i]

(ROOT / "event_windows.json").write_text(
    json.dumps(windows, indent=2) + "\n",
    encoding="utf-8",
)
PY
