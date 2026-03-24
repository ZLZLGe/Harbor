#!/bin/bash
set -euo pipefail

mkdir -p /outputs

python3 - <<'PY'
import json
import subprocess

INPUT_VIDEO = "/root/practice_review_feed.mp4"
LOGO = "/root/coaching_bug.png"
SPEC_JSON = "/root/replay_spec.json"
OUTPUT_VIDEO = "/outputs/coaching-replay.mp4"

with open(SPEC_JSON, "r", encoding="utf-8") as fh:
    spec = json.load(fh)

filter_complex = (
    f"[0:v]trim=start={spec['segment_start_sec']}:end={spec['segment_end_sec']},"
    f"setpts=PTS-STARTPTS,"
    f"crop={spec['crop_width_expr']}:{spec['crop_height_expr']}:{spec['crop_x_expr']}:{spec['crop_y_expr']},"
    f"scale={spec['output_width']}:{spec['output_height']},"
    f"setpts={spec['slowdown_factor']}*PTS[base];"
    f"[1:v]scale={spec['logo_width']}:-1[logo];"
    f"[base][logo]overlay={spec['overlay_x']}:{spec['overlay_y']}[v]"
)

subprocess.check_call(
    [
        "ffmpeg",
        "-y",
        "-i",
        INPUT_VIDEO,
        "-i",
        LOGO,
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        OUTPUT_VIDEO,
    ]
)
PY
