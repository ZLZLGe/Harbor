import cv2
import numpy as np

WIDTH = 352
HEIGHT = 192
FPS = 15
TOTAL_FRAMES = 105
OUTPUT_PATH = "/root/input.mp4"

BELT_TOP = 74
BELT_BOTTOM = 142


def state_for_frame(frame_id: int) -> str:
    if frame_id < 15:
        return "Empty"
    if frame_id < 48:
        return "Flowing"
    if frame_id < 72:
        return "Backlog"
    if frame_id < 93:
        return "Flowing"
    return "Empty"


def clamp_box(x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int, int]:
    return max(0, x0), max(0, y0), min(WIDTH, x1), min(HEIGHT, y1)


def draw_background(frame: np.ndarray, frame_id: int) -> None:
    frame[:] = (226, 224, 216)
    cv2.rectangle(frame, (0, 0), (WIDTH - 1, 46), (206, 210, 202), -1)
    cv2.rectangle(frame, (0, 46), (WIDTH - 1, HEIGHT - 1), (232, 230, 222), -1)

    for panel_x in (22, 112, 202, 292):
        cv2.rectangle(frame, (panel_x, 12), (panel_x + 38, 36), (82, 96, 104), -1)
        cv2.circle(frame, (panel_x + 10, 24), 4, (74, 188, 126), -1)
        cv2.circle(frame, (panel_x + 20, 24), 4, (82, 178, 236), -1)
        cv2.circle(frame, (panel_x + 30, 24), 4, (232, 224, 92), -1)

    cv2.rectangle(frame, (0, BELT_TOP), (WIDTH - 1, BELT_BOTTOM), (78, 84, 88), -1)
    cv2.rectangle(frame, (0, BELT_TOP - 8), (WIDTH - 1, BELT_TOP - 2), (120, 126, 130), -1)
    cv2.rectangle(frame, (0, BELT_BOTTOM + 2), (WIDTH - 1, BELT_BOTTOM + 8), (120, 126, 130), -1)

    stripe_shift = (frame_id * 8) % 30
    for x in range(-40, WIDTH + 40, 30):
        px = x + stripe_shift
        polygon = np.array(
            [
                [px, BELT_TOP + 4],
                [px + 14, BELT_TOP + 4],
                [px + 34, BELT_BOTTOM - 4],
                [px + 20, BELT_BOTTOM - 4],
            ],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(frame, polygon, (92, 98, 102))

    for y in (60, 156):
        cv2.line(frame, (0, y), (WIDTH - 1, y), (190, 188, 180), 2)
    for x in range(24, WIDTH, 64):
        cv2.line(frame, (x, 46), (x, HEIGHT - 1), (214, 212, 204), 1)


def draw_box(frame: np.ndarray, x: int, y: int, w: int, h: int, tone_shift: int) -> None:
    x0, y0, x1, y1 = clamp_box(x, y, x + w, y + h)
    if x0 >= x1 or y0 >= y1:
        return

    body_color = (42 + tone_shift, 146 + tone_shift // 3, 236)
    cv2.rectangle(frame, (x0, y0), (x1, y1), body_color, -1)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (26, 88, 150), 2)
    cv2.rectangle(frame, (x0 + 4, y0 + 4), (min(x1 - 2, x0 + 10), y1 - 4), (92, 194, 250), -1)


def draw_flowing_boxes(frame: np.ndarray, frame_id: int, phase_offset: float) -> None:
    local = frame_id + phase_offset
    widths = [24, 28, 22, 26]
    heights = [18, 20, 18, 20]
    spacing = 94.0
    speed = 6.0
    for idx, (width, height) in enumerate(zip(widths, heights)):
        raw_x = (idx * spacing + local * speed) % (WIDTH + spacing) - 42
        x = int(round(raw_x))
        y = 94 + (idx % 2) * 7
        draw_box(frame, x, y, width, height, tone_shift=idx * 4)


def draw_backlog_boxes(frame: np.ndarray, frame_id: int) -> None:
    lead_x = 34 + int(round((frame_id - 48) * 1.6))
    widths = [24, 26, 22, 28, 24, 26, 22]
    heights = [18, 20, 18, 20, 18, 20, 18]
    gaps = [4, 4, 3, 4, 3, 4, 3]
    x = lead_x
    for idx, (width, height) in enumerate(zip(widths, heights)):
        y = 92 + (idx % 3) * 4
        draw_box(frame, x, y, width, height, tone_shift=6 + idx * 3)
        x += width + gaps[idx]


def main() -> None:
    writer = cv2.VideoWriter(
        OUTPUT_PATH,
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT),
    )
    if not writer.isOpened():
        raise RuntimeError("failed to open video writer")

    for frame_id in range(TOTAL_FRAMES):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_background(frame, frame_id)

        state = state_for_frame(frame_id)
        if state == "Flowing":
            phase_offset = -15 if frame_id < 48 else 11
            draw_flowing_boxes(frame, frame_id, phase_offset)
        elif state == "Backlog":
            draw_backlog_boxes(frame, frame_id)

        writer.write(frame)

    writer.release()


if __name__ == "__main__":
    main()
