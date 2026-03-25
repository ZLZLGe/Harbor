#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import sys

sys.path.insert(0, "/root")
from activity_cleanup import build_padded_cues, clean_segments, load_csv_rows, load_json

config = load_json("/root/cue_config.json")
raw_segments = load_csv_rows("/root/pickup_boundaries.tsv", delimiter="\t")
speech_segments = clean_segments(raw_segments, gap_threshold=0.25, min_duration=0.30)
cues = build_padded_cues(
    speech_segments,
    pre_roll=float(config["pre_roll_sec"]),
    post_roll=float(config["post_roll_sec"]),
    clip_end=float(config["clip_duration_sec"]),
)

with open("/root/pickup_cues.tsv", "w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t")
    writer.writerow(
        [
            "cue_id",
            "start_sec",
            "end_sec",
            "duration_sec",
            "source_segment_count",
            "source_segments",
        ]
    )
    for cue in cues:
        writer.writerow(
            [
                cue["cue_id"],
                cue["start_sec"],
                cue["end_sec"],
                cue["duration_sec"],
                cue["source_segment_count"],
                ";".join(cue["source_segments"]),
            ]
        )
PY
