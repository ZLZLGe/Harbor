#!/bin/bash

set -euo pipefail

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

import cv2
from openpyxl import Workbook


WORKSPACE = Path("/app/workspace")
CONFIG_PATH = WORKSPACE / "assembly_line_assets" / "cap_audit_config.json"
OUTPUT_PATH = WORKSPACE / "cap_audit.xlsx"


def build_mask(hsv_image, color_name: str):
    if color_name == "red":
        mask_1 = cv2.inRange(hsv_image, (0, 120, 120), (10, 255, 255))
        mask_2 = cv2.inRange(hsv_image, (170, 120, 120), (180, 255, 255))
        return cv2.bitwise_or(mask_1, mask_2)
    if color_name == "blue":
        return cv2.inRange(hsv_image, (90, 120, 120), (125, 255, 255))
    raise ValueError(color_name)


def count_caps(crop, color_name: str) -> int:
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = build_mask(hsv, color_name)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    component_count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    hits = 0
    for label in range(1, component_count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        if area >= 250 and 12 <= width <= 48 and 12 <= height <= 48:
            hits += 1
    return hits


config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
video_path = WORKSPACE / "assembly_line_assets" / config["video_file"]
frame_dir = WORKSPACE / config["frame_output_dir"]
frame_dir.mkdir(parents=True, exist_ok=True)

x1, y1, x2, y2 = config["conveyor_region"]
sample_interval_seconds = int(config["sample_interval_seconds"])

cap = cv2.VideoCapture(str(video_path))
if not cap.isOpened():
    raise SystemExit(f"cannot open video: {video_path}")

fps = cap.get(cv2.CAP_PROP_FPS)
if fps <= 0:
    raise SystemExit("invalid video fps")

interval_frames = max(1, int(round(fps * sample_interval_seconds)))
rows = []
frame_index = 0
beat_index = 1

while True:
    ok, frame = cap.read()
    if not ok:
        break

    if frame_index % interval_frames == 0:
        crop = frame[y1:y2, x1:x2]
        frame_rel = f"{config['frame_output_dir']}/beat_{beat_index:02d}.jpg"
        cv2.imwrite(str(WORKSPACE / frame_rel), crop)

        red_caps = count_caps(crop, "red")
        blue_caps = count_caps(crop, "blue")
        timestamp_seconds = (beat_index - 1) * sample_interval_seconds
        rows.append([
            beat_index,
            f"{timestamp_seconds // 3600:02d}:{(timestamp_seconds % 3600) // 60:02d}:{timestamp_seconds % 60:02d}",
            frame_rel,
            red_caps,
            blue_caps,
            red_caps + blue_caps,
        ])
        beat_index += 1

    frame_index += 1

cap.release()

total_red = sum(row[3] for row in rows)
total_blue = sum(row[4] for row in rows)
total_caps = sum(row[5] for row in rows)

wb = Workbook()
ws = wb.active
ws.title = config["sheet_name"]
ws.append(["beat_index", "timestamp", "frame_file", "red_caps", "blue_caps", "total_caps"])
for row in rows:
    ws.append(row)
ws.append(["TOTAL", "", "", total_red, total_blue, total_caps])
wb.save(OUTPUT_PATH)
PY
