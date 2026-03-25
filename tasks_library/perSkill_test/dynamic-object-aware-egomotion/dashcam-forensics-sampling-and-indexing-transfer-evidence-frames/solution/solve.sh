#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import subprocess
from pathlib import Path

ROOT = Path("/root")
VIDEO_PATH = ROOT / "dashcam_clip.mp4"
MANIFEST_PATH = ROOT / "evidence_manifest.json"
EVENTS_PATH = ROOT / "incident_times.json"
OUTPUT_JSON = ROOT / "evidence_index.json"
OUTPUT_DIR = ROOT / "evidence_frames"


def sample_record(sample_index: int, manifest: dict) -> dict:
    frame_id = int(manifest["sample_offset_frame"]) + sample_index * int(manifest["sample_stride_frames"])
    timestamp_ms = int(round(frame_id * 1000.0 / float(manifest["video_fps"])))
    return {
        "sample_index": sample_index,
        "frame_id": frame_id,
        "sample_timestamp_ms": timestamp_ms,
        "jpeg_path": f"/root/evidence_frames/sample_{sample_index}.jpg",
    }


def choose_nearest_sample(event_time_ms: int, manifest: dict) -> dict:
    best = None
    for sample_index in range(int(manifest["sample_count"])):
        record = sample_record(sample_index, manifest)
        candidate = (abs(int(event_time_ms) - record["sample_timestamp_ms"]), sample_index, record)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[2]


def export_frame(frame_id: int, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(VIDEO_PATH),
        "-vf",
        f"select=eq(n\\,{frame_id})",
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]
    subprocess.run(command, check=True)


with MANIFEST_PATH.open("r", encoding="utf-8") as f:
    manifest = json.load(f)

with EVENTS_PATH.open("r", encoding="utf-8") as f:
    events = json.load(f)

output_events = []
selected_samples = {}

for event in events:
    selected = choose_nearest_sample(int(event["event_time_ms"]), manifest)
    output_events.append(
        {
            "event_id": event["event_id"],
            "event_time_ms": int(event["event_time_ms"]),
            "sample_index": selected["sample_index"],
            "frame_id": selected["frame_id"],
            "sample_timestamp_ms": selected["sample_timestamp_ms"],
            "jpeg_path": selected["jpeg_path"],
        }
    )
    selected_samples[selected["sample_index"]] = selected

for sample_index in sorted(selected_samples):
    record = selected_samples[sample_index]
    export_frame(record["frame_id"], Path(record["jpeg_path"]))

result = {
    "sampling": {
        "video_fps": manifest["video_fps"],
        "sample_offset_frame": manifest["sample_offset_frame"],
        "sample_stride_frames": manifest["sample_stride_frames"],
        "sample_count": manifest["sample_count"],
    },
    "events": output_events,
}

with OUTPUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
PY
