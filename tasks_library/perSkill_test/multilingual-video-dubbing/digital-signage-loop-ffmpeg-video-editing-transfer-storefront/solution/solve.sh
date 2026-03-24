#!/bin/bash
set -euo pipefail

mkdir -p "${OUTPUT_DIR:-/outputs}" "${TMPDIR:-/tmp}/storefront-work"

python3 - <<'PY'
import json
import os
import subprocess

ROOT = os.environ.get("TASK_ROOT", "/root")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/outputs")
TMP_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "storefront-work")
PLAN_PATH = os.path.join(ROOT, "storefront_plan.json")
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "storefront_loop.mp4")


def run(cmd):
    subprocess.check_call(cmd)


def probe_duration(path):
    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                path,
            ],
            text=True,
        ).strip()
    )


with open(PLAN_PATH, "r", encoding="utf-8") as f:
    plan = json.load(f)

canvas = plan["canvas"]
width = canvas["width"]
height = canvas["height"]
frame_rate = canvas["frame_rate"]
sample_rate = canvas["audio_sample_rate_hz"]
channels = canvas["audio_channels"]

os.makedirs(TMP_DIR, exist_ok=True)
segment_paths = []

for idx, clip in enumerate(plan["clips"]):
    input_path = os.path.join(ROOT, clip["file"])
    output_path = os.path.join(TMP_DIR, f"segment_{idx}.mkv")
    target = float(clip["target_duration_sec"])
    source_duration = probe_duration(input_path)

    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={frame_rate},format=yuv420p"
    )
    audio_filter = f"aresample={sample_rate}"

    if source_duration < target:
        pad_duration = target - source_duration
        video_filter = f"{video_filter},tpad=stop_mode=clone:stop_duration={pad_duration:.3f}"
        audio_filter = f"{audio_filter},apad=pad_dur={pad_duration:.3f}"

    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            input_path,
            "-vf",
            video_filter,
            "-af",
            audio_filter,
            "-t",
            f"{target:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(frame_rate),
            "-c:a",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            output_path,
        ]
    )
    segment_paths.append(output_path)

concat_list = os.path.join(TMP_DIR, "concat.txt")
with open(concat_list, "w", encoding="utf-8") as f:
    for path in segment_paths:
        f.write(f"file '{path}'\n")

run(
    [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(frame_rate),
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        OUTPUT_VIDEO,
    ]
)
PY
