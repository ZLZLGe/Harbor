#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "events.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "event_summary.csv"
output_dir.mkdir(parents=True, exist_ok=True)

groups = defaultdict(list)
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        start = datetime.fromisoformat(row["start_time"])
        end = datetime.fromisoformat(row["end_time"])
        duration_hours = (end - start).total_seconds() / 3600.0
        groups[row["event_type"]].append(
            {
                "severity": int(row["severity"]),
                "start_time": row["start_time"],
                "duration_hours": duration_hours,
            }
        )

summary_rows = []
for event_type in sorted(groups.keys()):
    items = groups[event_type]
    avg_duration = sum(x["duration_hours"] for x in items) / len(items)
    max_severity = max(x["severity"] for x in items)
    latest_start = max(x["start_time"] for x in items)
    summary_rows.append(
        {
            "event_type": event_type,
            "event_count": str(len(items)),
            "avg_duration_hours": f"{avg_duration:.3f}",
            "max_severity": str(max_severity),
            "latest_start_time": latest_start,
        }
    )

with output_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = [
        "event_type",
        "event_count",
        "avg_duration_hours",
        "max_severity",
        "latest_start_time",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)
PY
