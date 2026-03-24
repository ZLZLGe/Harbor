#!/bin/bash
set -euo pipefail

mkdir -p /outputs

python3 - <<'PY'
import json
import subprocess

INPUT_VIDEO = "/root/lobby_camera.mp4"
SCHEDULE_JSON = "/root/redaction_schedule.json"
OUTPUT_VIDEO = "/outputs/privacy-redaction-review.mp4"


def ffprobe_json(path):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                path,
            ],
            text=True,
        )
    )


def expr(intervals):
    return "+".join(
        f"between(t,{start:.3f},{end:.3f})"
        for start, end in intervals
    )


meta = ffprobe_json(INPUT_VIDEO)
video_stream = next(stream for stream in meta["streams"] if stream["codec_type"] == "video")
width = int(video_stream["width"])
height = int(video_stream["height"])
duration = float(meta["format"]["duration"])

with open(SCHEDULE_JSON, "r", encoding="utf-8") as fh:
    schedule = json.load(fh)

regions = schedule["regions"]
dim_alpha = float(schedule["dim_alpha"])

split_labels = ["base_src"] + [f"r{idx}src" for idx in range(len(regions))]
filter_parts = [
    f"[0:v]split={len(split_labels)}{''.join(f'[{label}]' for label in split_labels)}",
    f"color=c=black@{dim_alpha}:s={width}x{height}:d={duration:.3f}[shade]",
]

all_intervals = []
for region in regions:
    all_intervals.extend(region["intervals"])

filter_parts.append(
    f"[base_src][shade]overlay=0:0:enable='{expr(all_intervals)}'[v0]"
)

current_label = "v0"
for index, region in enumerate(regions):
    region_label = f"r{index}"
    output_label = "v" if index == len(regions) - 1 else f"v{index + 1}"
    filter_parts.append(
        f"[{region_label}src]crop={region['w']}:{region['h']}:{region['x']}:{region['y']},"
        f"gblur=sigma=18:steps=2[{region_label}]"
    )
    filter_parts.append(
        f"[{current_label}][{region_label}]overlay={region['x']}:{region['y']}:"
        f"enable='{expr(region['intervals'])}'[{output_label}]"
    )
    current_label = output_label

subprocess.check_call(
    [
        "ffmpeg",
        "-y",
        "-i",
        INPUT_VIDEO,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[v]",
        "-map",
        "0:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        OUTPUT_VIDEO,
    ]
)
PY
