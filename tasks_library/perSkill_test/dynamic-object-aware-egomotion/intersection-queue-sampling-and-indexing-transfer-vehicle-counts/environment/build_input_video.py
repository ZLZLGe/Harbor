import cv2
import numpy as np

WIDTH = 360
HEIGHT = 240
FPS = 12
TOTAL_FRAMES = 84
OUTPUT_PATH = "/root/input.mp4"

ROAD_LEFT = 128
ROAD_RIGHT = 232
STOP_LINE_Y = 168
LANE_CENTER_X = 180
CAR_WIDTH = 28
CAR_HEIGHT = 30
SAMPLE_STEP = 4
SAMPLE_COUNTS = [
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    4,
    3,
    2,
    2,
    1,
    0,
    0,
    1,
    2,
    3,
    2,
    1,
]
QUEUE_BOTTOMS = [158, 120, 82, 44]


def queue_count_for_frame(frame_id: int) -> int:
    block_index = min(frame_id // SAMPLE_STEP, len(SAMPLE_COUNTS) - 1)
    return SAMPLE_COUNTS[block_index]


def draw_background(frame: np.ndarray, frame_id: int) -> None:
    frame[:] = (184, 198, 210)
    cv2.rectangle(frame, (0, 0), (WIDTH - 1, 52), (166, 184, 198), -1)
    cv2.rectangle(frame, (0, 52), (WIDTH - 1, HEIGHT - 1), (152, 172, 148), -1)

    cv2.rectangle(frame, (ROAD_LEFT, 0), (ROAD_RIGHT, HEIGHT - 1), (68, 72, 76), -1)
    cv2.rectangle(frame, (0, STOP_LINE_Y - 8), (WIDTH - 1, HEIGHT - 1), (74, 78, 82), -1)

    cv2.line(frame, (ROAD_LEFT, 0), (ROAD_LEFT, HEIGHT - 1), (120, 124, 128), 2)
    cv2.line(frame, (ROAD_RIGHT, 0), (ROAD_RIGHT, HEIGHT - 1), (120, 124, 128), 2)
    cv2.line(frame, (LANE_CENTER_X, 0), (LANE_CENTER_X, STOP_LINE_Y - 18), (210, 214, 218), 2)
    cv2.line(frame, (ROAD_LEFT, STOP_LINE_Y), (ROAD_RIGHT, STOP_LINE_Y), (248, 248, 248), 4)

    for stripe_x in range(ROAD_LEFT + 6, ROAD_RIGHT - 18, 18):
        cv2.rectangle(frame, (stripe_x, STOP_LINE_Y + 8), (stripe_x + 8, STOP_LINE_Y + 36), (236, 236, 236), -1)

    for y in range(18, STOP_LINE_Y - 8, 28):
        cv2.line(frame, (ROAD_LEFT + 18, y), (ROAD_LEFT + 18, y + 12), (216, 216, 92), 2)
        cv2.line(frame, (ROAD_RIGHT - 18, y), (ROAD_RIGHT - 18, y + 12), (216, 216, 92), 2)

    cv2.rectangle(frame, (34, 28), (78, 94), (52, 58, 62), -1)
    cycle = (frame_id // SAMPLE_STEP) % 6
    red_on = cycle in {0, 1, 2, 3}
    green_on = not red_on
    cv2.circle(frame, (56, 48), 9, (0, 0, 210 if red_on else 70), -1)
    cv2.circle(frame, (56, 74), 9, (0, 210 if green_on else 70, 0), -1)


def draw_cross_traffic(frame: np.ndarray, frame_id: int) -> None:
    lane_y = [182, 204]
    colors = [(218, 140, 52), (174, 96, 210), (212, 182, 66)]
    for idx, offset in enumerate((0, 120, 238)):
        x = int((frame_id * 7 + offset) % (WIDTH + 72)) - 36
        y = lane_y[idx % 2]
        cv2.rectangle(frame, (x, y), (x + 36, y + 18), colors[idx], -1)
        cv2.rectangle(frame, (x + 8, y + 4), (x + 28, y + 14), (232, 232, 236), -1)


def draw_queue_vehicle(frame: np.ndarray, slot_index: int, frame_id: int) -> None:
    bottom = QUEUE_BOTTOMS[slot_index]
    top = bottom - CAR_HEIGHT
    x_shift = (-2, 1, -3, 2)[slot_index]
    idle_wobble = ((frame_id + slot_index) % 3) - 1
    x0 = LANE_CENTER_X - CAR_WIDTH // 2 + x_shift + idle_wobble
    x1 = x0 + CAR_WIDTH

    cv2.rectangle(frame, (x0, top), (x1, bottom), (28, 150, 242), -1)
    cv2.rectangle(frame, (x0 + 4, top + 5), (x1 - 4, top + 15), (198, 224, 238), -1)
    cv2.rectangle(frame, (x0 + 3, top + 18), (x1 - 3, bottom - 4), (24, 120, 214), 2)
    cv2.circle(frame, (x0 + 5, bottom), 3, (26, 28, 30), -1)
    cv2.circle(frame, (x1 - 5, bottom), 3, (26, 28, 30), -1)


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
        draw_cross_traffic(frame, frame_id)

        queue_count = queue_count_for_frame(frame_id)
        for slot_index in range(queue_count):
            draw_queue_vehicle(frame, slot_index, frame_id)

        writer.write(frame)

    writer.release()


if __name__ == "__main__":
    main()
