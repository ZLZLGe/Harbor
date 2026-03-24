#!/bin/bash

set -euo pipefail

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

import cv2


WORKSPACE = Path("/app/workspace")
CONFIG_PATH = WORKSPACE / "traffic_signal_config.json"
VIDEO_DIR = WORKSPACE / "traffic_videos"
FRAME_ROOT = WORKSPACE / "sampled_frames"
OUTPUT_PATH = WORKSPACE / "traffic_phase_counts.json"


def detect_state(frame, roi):
    x1, y1, x2, y2 = roi
    crop = frame[y1:y2, x1:x2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    red_mask = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255)) | cv2.inRange(hsv, (170, 80, 80), (180, 255, 255))
    yellow_mask = cv2.inRange(hsv, (18, 80, 80), (40, 255, 255))
    green_mask = cv2.inRange(hsv, (45, 60, 60), (95, 255, 255))

    scores = {
        "red": int(cv2.countNonZero(red_mask)),
        "yellow": int(cv2.countNonZero(yellow_mask)),
        "green": int(cv2.countNonZero(green_mask)),
    }
    return max(scores, key=scores.get)


config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
sample_interval_seconds = config["sample_interval_seconds"]

videos_output = []
FRAME_ROOT.mkdir(parents=True, exist_ok=True)

for video_spec in sorted(config["videos"], key=lambda item: item["video_file"]):
    video_file = video_spec["video_file"]
    video_path = VIDEO_DIR / video_file
    frame_dir = FRAME_ROOT / Path(video_file).stem
    frame_dir.mkdir(parents=True, exist_ok=True)

    phase_counts = {
        signal["direction"]: {"red": 0, "yellow": 0, "green": 0}
        for signal in video_spec["signals"]
    }

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval_frames = max(1, int(round(fps * sample_interval_seconds)))

    frame_index = 0
    sampled_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % interval_frames == 0:
            output_frame = frame_dir / f"frame_{sampled_index:03d}.jpg"
            cv2.imwrite(str(output_frame), frame)
            for signal in video_spec["signals"]:
                state = detect_state(frame, signal["roi"])
                phase_counts[signal["direction"]][state] += 1
            sampled_index += 1
        frame_index += 1
    cap.release()

    videos_output.append(
        {
            "video_file": video_file,
            "sampled_frames_dir": f"sampled_frames/{Path(video_file).stem}",
            "sampled_frame_count": sampled_index,
            "phase_counts": phase_counts,
        }
    )

OUTPUT_PATH.write_text(
    json.dumps(
        {
            "sample_interval_seconds": sample_interval_seconds,
            "videos": videos_output,
        },
        indent=2,
    ) + "\n",
    encoding="utf-8",
)
PY
