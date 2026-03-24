from pathlib import Path
import math

import cv2
import numpy as np


WORKSPACE = Path("/app/workspace/lecture_assets")
VIDEO_PATH = WORKSPACE / "lecture_week3.avi"
WIDTH = 960
HEIGHT = 540
FPS = 6
TOTAL_SECONDS = 18
SLIDE_REGION = (40, 40, 760, 440)
SLIDES = [
    {
        "start_second": 0,
        "title": "Week 3: Linear Models",
        "bullets": [
            "Feature scaling and bias terms",
            "Normal equation overview",
            "When matrix inversion is unstable",
        ],
        "background": (212, 178, 114),
        "accent": (96, 78, 28),
        "marker": (180, 90, 40),
    },
    {
        "start_second": 4,
        "title": "Ordinary Least Squares",
        "bullets": [
            "Minimize squared residual sum",
            "Design matrix X and target y",
            "Closed-form solution review",
        ],
        "background": (176, 209, 133),
        "accent": (44, 108, 38),
        "marker": (70, 175, 55),
    },
    {
        "start_second": 9,
        "title": "Residual Diagnostics",
        "bullets": [
            "Watch for heteroscedasticity",
            "Inspect leverage and outliers",
            "Plot residuals against fitted values",
        ],
        "background": (112, 191, 239),
        "accent": (22, 94, 150),
        "marker": (0, 145, 255),
    },
    {
        "start_second": 13,
        "title": "Exam Review Checklist",
        "bullets": [
            "Interpret coefficients carefully",
            "Compare train and validation error",
            "State modeling assumptions clearly",
        ],
        "background": (168, 158, 235),
        "accent": (84, 56, 150),
        "marker": (35, 35, 215),
    },
]


def slide_for_second(second: int) -> dict:
    current = SLIDES[0]
    for slide in SLIDES:
        if second >= slide["start_second"]:
            current = slide
    return current


def draw_slide(frame: np.ndarray, slide: dict, frame_index: int) -> None:
    x1, y1, x2, y2 = SLIDE_REGION
    cv2.rectangle(frame, (x1, y1), (x2, y2), slide["background"], -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (248, 248, 248), 3)

    cv2.rectangle(frame, (x1 + 24, y1 + 24), (x1 + 92, y1 + 92), slide["marker"], -1)
    cv2.rectangle(frame, (x1 + 120, y1 + 40), (x2 - 32, y1 + 104), (245, 245, 245), -1)
    cv2.putText(frame, slide["title"], (x1 + 138, y1 + 84), cv2.FONT_HERSHEY_SIMPLEX, 0.9, slide["accent"], 2, cv2.LINE_AA)

    chart_origin = (x1 + 84, y1 + 190)
    chart_height = 126
    chart_width = 260
    cv2.line(frame, (chart_origin[0], chart_origin[1]), (chart_origin[0], chart_origin[1] + chart_height), slide["accent"], 2)
    cv2.line(frame, (chart_origin[0], chart_origin[1] + chart_height), (chart_origin[0] + chart_width, chart_origin[1] + chart_height), slide["accent"], 2)
    points = [
        (chart_origin[0] + 20, chart_origin[1] + 102),
        (chart_origin[0] + 70, chart_origin[1] + 82),
        (chart_origin[0] + 125, chart_origin[1] + 58),
        (chart_origin[0] + 190, chart_origin[1] + 34),
        (chart_origin[0] + 240, chart_origin[1] + 18),
    ]
    for start, end in zip(points, points[1:]):
        cv2.line(frame, start, end, slide["marker"], 4)
    for point in points:
        cv2.circle(frame, point, 6, (245, 245, 245), -1)
        cv2.circle(frame, point, 3, slide["marker"], -1)

    for idx, bullet in enumerate(slide["bullets"], start=0):
        y = y1 + 176 + idx * 76
        cv2.circle(frame, (x1 + 430, y - 10), 7, slide["marker"], -1)
        cv2.putText(frame, bullet, (x1 + 452, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, slide["accent"], 2, cv2.LINE_AA)

    cursor_x = x1 + 165 + int(20 * math.sin(frame_index / 3))
    cursor_y = y1 + 146 + int(14 * math.cos(frame_index / 4))
    cv2.circle(frame, (cursor_x, cursor_y), 7, (35, 35, 220), -1)


def draw_speaker_and_status(frame: np.ndarray, second: float, frame_index: int) -> None:
    cv2.rectangle(frame, (790, 52), (925, 228), (36, 39, 44), -1)
    cv2.rectangle(frame, (790, 52), (925, 228), (205, 205, 205), 2)

    bob = int(8 * math.sin(frame_index / 5))
    face_center = (858, 126 + bob)
    cv2.circle(frame, face_center, 45, (86, 145, 220), -1)
    cv2.circle(frame, (face_center[0] - 16, face_center[1] - 10), 6, (255, 255, 255), -1)
    cv2.circle(frame, (face_center[0] + 16, face_center[1] - 10), 6, (255, 255, 255), -1)
    cv2.ellipse(frame, (face_center[0], face_center[1] + 15), (20, 14), 0, 0, 180, (255, 255, 255), 3)
    cv2.rectangle(frame, (812, 176 + bob), (904, 212 + bob), (118, 84, 196), -1)

    cv2.putText(frame, "Instructor Cam", (798, 248), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (250, 250, 250), 1, cv2.LINE_AA)

    cv2.rectangle(frame, (0, 480), (WIDTH, HEIGHT), (24, 26, 30), -1)
    pulse = 180 + int(60 * math.sin(frame_index / 2))
    cv2.circle(frame, (46, 510), 10, (30, 30, pulse), -1)
    cv2.putText(frame, "REC", (64, 516), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (245, 245, 245), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Week 3 Recording   {second:05.1f}s", (150, 516), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (232, 232, 232), 2, cv2.LINE_AA)


def build_video() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(VIDEO_PATH), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create video at {VIDEO_PATH}")

    total_frames = FPS * TOTAL_SECONDS
    for frame_index in range(total_frames):
        second = frame_index / FPS
        slide = slide_for_second(int(second))
        frame = np.full((HEIGHT, WIDTH, 3), 245, dtype=np.uint8)

        draw_slide(frame, slide, frame_index)
        draw_speaker_and_status(frame, second, frame_index)

        writer.write(frame)

    writer.release()


if __name__ == "__main__":
    build_video()
