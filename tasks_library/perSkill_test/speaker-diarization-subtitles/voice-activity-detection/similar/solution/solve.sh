#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import sys

sys.path.insert(0, "/root")
from activity_cleanup import clean_segments, load_json, round3

payload = load_json("/root/raw_activity_draft.json")
speech_segments = clean_segments(payload["segments"], gap_threshold=0.25, min_duration=0.30)

result = {
    "clip_id": payload["clip_id"],
    "segment_count": len(speech_segments),
    "total_speech_sec": round3(sum(item["duration_sec"] for item in speech_segments)),
    "first_start_sec": speech_segments[0]["start_sec"] if speech_segments else 0.0,
    "last_end_sec": speech_segments[-1]["end_sec"] if speech_segments else 0.0,
    "speech_segments": speech_segments,
}

with open("/root/final_speech_segments.json", "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
PY
