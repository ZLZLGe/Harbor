#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import sys

sys.path.insert(0, "/root")
from activity_cleanup import compute_silence_windows, clean_segments, load_csv_rows, load_json

region = load_json("/root/review_region.json")
raw_segments = load_csv_rows("/root/activity_pass1.csv")
speech_segments = clean_segments(raw_segments, gap_threshold=0.25, min_duration=0.30)
silence_windows = compute_silence_windows(
    speech_segments,
    float(region["review_start_sec"]),
    float(region["review_end_sec"]),
    min_duration=0.40,
)

with open("/root/review_silence_windows.csv", "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "silence_id",
            "start_sec",
            "end_sec",
            "duration_sec",
            "left_context",
            "right_context",
        ],
    )
    writer.writeheader()
    writer.writerows(silence_windows)
PY
