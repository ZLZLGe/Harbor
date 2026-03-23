#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys

sys.path.insert(0, "/root")
from activity_cleanup import clean_segments, load_json, load_jsonl, round3

config = load_json("/root/audit_config.json")
speech_segments = clean_segments(load_jsonl("/root/burst_activity.jsonl"), gap_threshold=0.25, min_duration=0.30)

quiet_gap_threshold = float(config["quiet_gap_threshold_sec"])
micro_burst_threshold = float(config["micro_burst_threshold_sec"])

segments_after_quiet_gap = []
longest_quiet_gap_sec = 0.0
for previous, current in zip(speech_segments, speech_segments[1:]):
    gap_sec = round3(float(current["start_sec"]) - float(previous["end_sec"]))
    longest_quiet_gap_sec = max(longest_quiet_gap_sec, gap_sec)
    if gap_sec + 1e-9 >= quiet_gap_threshold:
        segments_after_quiet_gap.append(
            {
                "segment_id": current["segment_id"],
                "gap_sec": gap_sec,
            }
        )

phase_totals = {
    "phase_1_under_30": 0.0,
    "phase_2_30_to_60": 0.0,
    "phase_3_60_plus": 0.0,
}
micro_bursts = []
for segment in speech_segments:
    start_sec = float(segment["start_sec"])
    duration_sec = float(segment["duration_sec"])
    if start_sec < 30.0:
        phase_totals["phase_1_under_30"] += duration_sec
    elif start_sec < 60.0:
        phase_totals["phase_2_30_to_60"] += duration_sec
    else:
        phase_totals["phase_3_60_plus"] += duration_sec

    if duration_sec < micro_burst_threshold:
        micro_bursts.append(segment["segment_id"])

result = {
    "kept_segment_count": len(speech_segments),
    "total_speech_sec": round3(sum(item["duration_sec"] for item in speech_segments)),
    "first_speech_sec": speech_segments[0]["start_sec"] if speech_segments else 0.0,
    "last_speech_sec": speech_segments[-1]["end_sec"] if speech_segments else 0.0,
    "longest_quiet_gap_sec": round3(longest_quiet_gap_sec),
    "segments_after_quiet_gap": segments_after_quiet_gap,
    "micro_bursts": micro_bursts,
    "phase_totals_sec": {
        key: round3(value) for key, value in phase_totals.items()
    },
}

with open("/root/activity_burst_audit.json", "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
PY
