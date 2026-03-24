from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


WIDTH = 640
HEIGHT = 360
FPS = 12
SAMPLE_INTERVAL_SECONDS = 3
SEGMENT_SECONDS = SAMPLE_INTERVAL_SECONDS
BEAT_LAYOUTS = [
    {"red": [130, 290], "blue": [455]},
    {"red": [175], "blue": [315, 445, 535]},
    {"red": [110, 230, 360, 500], "blue": []},
    {"red": [], "blue": [245, 425]},
    {"red": [145, 310, 515], "blue": [230, 420]},
    {"red": [345], "blue": [495]},
]
ROI = [40, 120, 600, 280]
OUTPUT_DIR = Path("/app/workspace/assembly_line_assets")


def draw_background(frame: np.ndarray, phase: int) -> None:
    frame[:] = (234, 236, 239)
    cv2.rectangle(frame, (0, 0), (WIDTH, 94), (222, 226, 232), thickness=-1)
    cv2.rectangle(frame, (0, 286), (WIDTH, HEIGHT), (214, 218, 222), thickness=-1)
    cv2.rectangle(frame, (32, 116), (608, 286), (72, 78, 86), thickness=-1)
    cv2.rectangle(frame, (48, 138), (592, 266), (95, 101, 108), thickness=-1)

    for x in range(-40, WIDTH + 60, 72):
        offset = (x + phase * 9) % 96
        cv2.rectangle(frame, (offset - 28, 188), (offset + 18, 216), (118, 124, 132), thickness=-1)

    for x in (88, 214, 344, 474, 586):
        cv2.circle(frame, (x, 104), 16, (145, 149, 155), thickness=3)
    for x in (92, 224, 356, 488, 584):
        cv2.circle(frame, (x, 304), 14, (148, 152, 158), thickness=3)

    # Distracting status indicators outside the conveyor ROI.
    cv2.circle(frame, (52, 52), 16, (20, 20, 210), thickness=-1)
    cv2.circle(frame, (588, 58), 16, (210, 70, 20), thickness=-1)
    cv2.rectangle(frame, (520, 304), (616, 344), (60, 80, 115), thickness=-1)
    cv2.putText(frame, "LINE A", (68, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (70, 76, 84), 2, cv2.LINE_AA)
    cv2.putText(frame, "SHIFT B", (74, 334), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (86, 92, 98), 2, cv2.LINE_AA)


def draw_bottle(frame: np.ndarray, center_x: int, cap_color: tuple[int, int, int]) -> None:
    body_top = 154
    body_bottom = 248
    bottle_half_width = 21

    cv2.rectangle(
        frame,
        (center_x - bottle_half_width, body_top),
        (center_x + bottle_half_width, body_bottom),
        (245, 245, 245),
        thickness=-1,
    )
    cv2.rectangle(
        frame,
        (center_x - bottle_half_width, body_top),
        (center_x + bottle_half_width, body_bottom),
        (208, 210, 214),
        thickness=2,
    )
    cv2.rectangle(frame, (center_x - 10, 146), (center_x + 10, 160), (226, 228, 232), thickness=-1)
    cv2.circle(frame, (center_x, 150), 15, cap_color, thickness=-1)
    cv2.circle(frame, (center_x, 150), 15, (34, 34, 34), thickness=2)
    cv2.line(frame, (center_x - 12, 198), (center_x + 12, 198), (218, 220, 224), 2)


def write_video(video_path: Path) -> None:
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        FPS,
        (WIDTH, HEIGHT),
    )
    if not writer.isOpened():
        raise RuntimeError(f"cannot create video: {video_path}")

    red_bgr = (40, 40, 220)
    blue_bgr = (215, 115, 35)

    for segment_index, layout in enumerate(BEAT_LAYOUTS):
        frames_in_segment = FPS * SEGMENT_SECONDS
        for frame_in_segment in range(frames_in_segment):
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            draw_background(frame, phase=frame_in_segment)
            for x in layout["red"]:
                draw_bottle(frame, x, red_bgr)
            for x in layout["blue"]:
                draw_bottle(frame, x, blue_bgr)
            writer.write(frame)

    writer.release()


def write_config(config_path: Path) -> None:
    config = {
        "video_file": "line_patrol.avi",
        "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
        "conveyor_region": ROI,
        "frame_output_dir": "cap_audit_frames",
        "sheet_name": "audit",
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_video(OUTPUT_DIR / "line_patrol.avi")
    write_config(OUTPUT_DIR / "cap_audit_config.json")


if __name__ == "__main__":
    main()
