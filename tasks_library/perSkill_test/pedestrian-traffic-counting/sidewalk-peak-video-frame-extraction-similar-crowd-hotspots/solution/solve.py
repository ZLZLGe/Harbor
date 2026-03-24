#!/usr/bin/env python3

import os
from pathlib import Path

import cv2
from openpyxl import Workbook


VIDEO_EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv", ".webm"}
OUTPUT_PATH = Path("/app/video/pedestrian_peaks.xlsx")
FRAME_ROOT = Path("/tmp/pedestrian_peak_frames")


def extract_frames(video_path: Path) -> list[Path]:
    target_dir = FRAME_ROOT / video_path.stem
    target_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frame_paths: list[Path] = []
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frame_path = target_dir / f"frame_{frame_index:04d}.png"
        cv2.imwrite(str(frame_path), frame)
        frame_paths.append(frame_path)
        frame_index += 1

    capture.release()
    return frame_paths


def count_pedestrians(frame_path: Path) -> int:
    frame = cv2.imread(str(frame_path))
    if frame is None:
        raise RuntimeError(f"Cannot read frame: {frame_path}")

    red_mask = (
        (frame[:, :, 2] > 180)
        & (frame[:, :, 1] < 90)
        & (frame[:, :, 0] < 90)
    )
    mask = (red_mask.astype("uint8")) * 255
    component_count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    people = 0
    for label in range(1, component_count):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= 80:
            people += 1
    return people


def analyze_video(video_path: Path) -> tuple[str, str, int]:
    frame_paths = extract_frames(video_path)
    if not frame_paths:
        raise RuntimeError(f"No frames extracted from {video_path}")

    best_index = -1
    best_count = -1
    for frame_index, frame_path in enumerate(frame_paths):
        people = count_pedestrians(frame_path)
        if people > best_count:
            best_index = frame_index
            best_count = people

    return video_path.name, f"F{best_index:04d}", best_count


def write_workbook(rows: list[tuple[str, str, int]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "results"
    sheet.append(["filename", "peak_frame_id", "visible_pedestrians"])
    for row in rows:
        sheet.append(list(row))
    workbook.save(OUTPUT_PATH)


def main() -> int:
    video_dir = Path("/app/video")
    FRAME_ROOT.mkdir(parents=True, exist_ok=True)

    videos = sorted(
        path for path in video_dir.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )

    rows = [analyze_video(video_path) for video_path in videos]
    write_workbook(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
