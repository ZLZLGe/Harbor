import json
import math
import os
import re
from collections import deque
from functools import lru_cache
from pathlib import Path


INPUT_DIR = Path(os.getenv("TASK_INPUT_DIR", "/app/input"))
OUTPUT_PATH = Path(os.getenv("TASK_OUTPUT_PATH", "/app/output/near_miss_events.json"))
TIMESTAMP_PATTERN = re.compile(r"^\d{2}:\d{2}$")

WIDTH = 240
HEIGHT = 160
ROW_PAD = (4 - (WIDTH * 3) % 4) % 4
ROW_BYTES = WIDTH * 3 + ROW_PAD
LABEL_TEMPLATES = {
    "F1": (
        "##########......##..",
        "##########......##..",
        "##............####..",
        "##............####..",
        "##..............##..",
        "##..............##..",
        "########........##..",
        "########........##..",
        "##..............##..",
        "##..............##..",
        "##..............##..",
        "##..............##..",
        "##............######",
        "##............######",
    ),
    "F2": (
        "##########....######..",
        "##########....######..",
        "##..........##......##",
        "##..........##......##",
        "##..................##",
        "##..................##",
        "########..........##..",
        "########..........##..",
        "##..............##....",
        "##..............##....",
        "##............##......",
        "##............##......",
        "##..........##########",
        "##..........##########",
    ),
    "F3": (
        "##########..########..",
        "##########..########..",
        "##..................##",
        "##..................##",
        "##..................##",
        "##..................##",
        "########......######..",
        "########......######..",
        "##..................##",
        "##..................##",
        "##..................##",
        "##..................##",
        "##..........########..",
        "##..........########..",
    ),
    "F4": (
        "########....########..",
        "########....########..",
        "##......##..........##",
        "##......##..........##",
        "##......##..........##",
        "##......##..........##",
        "########......######..",
        "########......######..",
        "##..................##",
        "##..................##",
        "##..................##",
        "##..................##",
        "##..........########..",
        "##..........########..",
    ),
    "P1": (
        "########........##..",
        "########........##..",
        "##......##....####..",
        "##......##....####..",
        "##......##......##..",
        "##......##......##..",
        "########........##..",
        "########........##..",
        "##..............##..",
        "##..............##..",
        "##..............##..",
        "##..............##..",
        "##............######",
        "##............######",
    ),
    "P3": (
        "########..........##..",
        "########..........##..",
        "##......##......####..",
        "##......##......####..",
        "##......##....##..##..",
        "##......##....##..##..",
        "########....##....##..",
        "########....##....##..",
        "##..........##########",
        "##..........##########",
        "##................##..",
        "##................##..",
        "##................##..",
        "##................##..",
    ),
    "P4": (
        "##########........##..",
        "##########........##..",
        "##..............####..",
        "##..............####..",
        "##............##..##..",
        "##............##..##..",
        "########....##....##..",
        "########....##....##..",
        "##..........##########",
        "##..........##########",
        "##................##..",
        "##................##..",
        "##................##..",
        "##................##..",
    ),
}


def _load_policy(input_dir: Path) -> dict:
    return json.loads((input_dir / "near_miss_policy.json").read_text())


def _load_frames(video_path: Path) -> list[bytes]:
    data = video_path.read_bytes()
    movi_start = data.index(b"movi") + 4
    idx1_start = data.index(b"idx1")
    frames = []
    pos = movi_start

    while pos < idx1_start:
        tag = data[pos : pos + 4]
        size = int.from_bytes(data[pos + 4 : pos + 8], "little")
        payload_start = pos + 8
        payload_end = payload_start + size
        if tag == b"00db":
            frames.append(data[payload_start:payload_end])
        pos = payload_end + (size % 2)

    return frames


def _read_fps(video_path: Path) -> int:
    data = video_path.read_bytes()
    avih_index = data.index(b"avih") + 8
    microseconds_per_frame = int.from_bytes(data[avih_index : avih_index + 4], "little")
    if not microseconds_per_frame:
        return 1
    return max(1, round(1_000_000 / microseconds_per_frame))


def _rgb(frame: bytes, x: int, y: int) -> tuple[int, int, int]:
    row = HEIGHT - 1 - y
    base = row * ROW_BYTES + x * 3
    b, g, r = frame[base : base + 3]
    return (r, g, b)


def _component_stats(points: list[tuple[int, int]]) -> dict:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return {
        "n": len(points),
        "cx": sum(xs) / len(points),
        "cy": sum(ys) / len(points),
        "box": (min(xs), min(ys), max(xs), max(ys)),
    }


def _connected_components(frame: bytes, predicate, min_size: int) -> list[dict]:
    seen: set[tuple[int, int]] = set()
    components = []

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if (x, y) in seen or not predicate(*_rgb(frame, x, y)):
                continue

            queue = deque([(x, y)])
            seen.add((x, y))
            points = []

            while queue:
                current_x, current_y = queue.popleft()
                points.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x + 1, current_y),
                    (current_x - 1, current_y),
                    (current_x, current_y + 1),
                    (current_x, current_y - 1),
                    (current_x + 1, current_y + 1),
                    (current_x - 1, current_y - 1),
                    (current_x + 1, current_y - 1),
                    (current_x - 1, current_y + 1),
                ):
                    if (
                        0 <= next_x < WIDTH
                        and 0 <= next_y < HEIGHT
                        and (next_x, next_y) not in seen
                        and predicate(*_rgb(frame, next_x, next_y))
                    ):
                        seen.add((next_x, next_y))
                        queue.append((next_x, next_y))

            if len(points) >= min_size:
                components.append(_component_stats(points))

    return components


def _merge_pedestrian_fragments(components: list[dict]) -> list[dict]:
    remaining = sorted(components, key=lambda item: (item["cx"], item["cy"]))
    merged = []

    while remaining:
        current = remaining.pop(0)
        current_x1, current_y1, current_x2, current_y2 = current["box"]
        group = [current]
        keep = []

        for candidate in remaining:
            x1, y1, x2, y2 = candidate["box"]
            horizontal_overlap = min(current_x2, x2) - max(current_x1, x1)
            vertical_gap = max(y1 - current_y2, current_y1 - y2, 0)
            if horizontal_overlap >= -2 and vertical_gap <= 4 and abs(current["cx"] - candidate["cx"]) <= 6:
                group.append(candidate)
            else:
                keep.append(candidate)

        remaining = keep
        points = []
        for item in group:
            x1, y1, x2, y2 = item["box"]
            points.extend(((x1, y1), (x1, y2), (x2, y1), (x2, y2)))

        total_pixels = sum(item["n"] for item in group)
        merged.append(
            {
                "n": total_pixels,
                "cx": sum(item["cx"] * item["n"] for item in group) / total_pixels,
                "cy": sum(item["cy"] * item["n"] for item in group) / total_pixels,
                "box": (
                    min(point[0] for point in points),
                    min(point[1] for point in points),
                    max(point[0] for point in points),
                    max(point[1] for point in points),
                ),
            }
        )

    return merged


def _detect_forklifts(frame: bytes) -> list[dict]:
    return _connected_components(
        frame,
        lambda r, g, b: b > 120 and r < 90 and g < 140,
        min_size=100,
    )


def _detect_pedestrians(frame: bytes) -> list[dict]:
    components = _connected_components(
        frame,
        lambda r, g, b: (
            (r > 150 and g < 100 and b < 100)
            or (g > 100 and r < 100 and b < 100)
            or (r > 150 and 70 < g < 170 and b < 100)
        ),
        min_size=20,
    )
    merged = _merge_pedestrian_fragments(components)
    return [item for item in merged if not (item["cx"] < 70 and item["cy"] > 130)]


def _track_constant_count(sequence: list[list[dict]]) -> list[list[dict]]:
    tracks = [[item] for item in sequence[0]]
    for items in sequence[1:]:
        remaining = set(range(len(items)))
        for track in tracks:
            last = track[-1]
            best_index = min(
                remaining,
                key=lambda index: math.dist((last["cx"], last["cy"]), (items[index]["cx"], items[index]["cy"])),
            )
            track.append(items[best_index])
            remaining.remove(best_index)
    return tracks


def _trace_actor(sequence: list[list[dict]], start_index: int, actor: dict) -> list[dict]:
    track = [None] * len(sequence)
    current = actor
    track[start_index] = current

    for index in range(start_index - 1, -1, -1):
        current = min(
            sequence[index],
            key=lambda candidate: math.dist((candidate["cx"], candidate["cy"]), (current["cx"], current["cy"])),
        )
        track[index] = current

    current = actor
    for index in range(start_index + 1, len(sequence)):
        current = min(
            sequence[index],
            key=lambda candidate: math.dist((candidate["cx"], candidate["cy"]), (current["cx"], current["cy"])),
        )
        track[index] = current

    return track


def _label_boxes(frame: bytes) -> list[tuple[int, int, int, int]]:
    components = _connected_components(
        frame,
        lambda r, g, b: r > 240 and g > 240 and b > 240,
        min_size=250,
    )
    boxes = []
    for component in components:
        x1, y1, x2, y2 = component["box"]
        width = x2 - x1 + 1
        height = y2 - y1 + 1
        if component["n"] <= 400 and width <= 32 and height <= 22:
            boxes.append(component["box"])
    return boxes


def _trim_black_mask(frame: bytes, box: tuple[int, int, int, int]) -> tuple[str, ...]:
    x1, y1, x2, y2 = box
    black_pixels = []
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            r, g, b = _rgb(frame, x, y)
            if r < 50 and g < 50 and b < 50:
                black_pixels.append((x - x1, y - y1))

    if not black_pixels:
        return tuple()

    trim_x1 = min(point[0] for point in black_pixels)
    trim_y1 = min(point[1] for point in black_pixels)
    trim_x2 = max(point[0] for point in black_pixels)
    trim_y2 = max(point[1] for point in black_pixels)
    black_set = set(black_pixels)

    rows = []
    for y in range(trim_y1, trim_y2 + 1):
        row = []
        for x in range(trim_x1, trim_x2 + 1):
            row.append("#" if (x, y) in black_set else ".")
        rows.append("".join(row))
    return tuple(rows)


def _recognize_label(frame: bytes, box: tuple[int, int, int, int]) -> str | None:
    rows = _trim_black_mask(frame, box)
    if not rows:
        return None

    best_label = None
    best_score = None
    for label, template in LABEL_TEMPLATES.items():
        height = max(len(rows), len(template))
        width = max(len(rows[0]), len(template[0]))
        score = 0
        for y in range(height):
            row_a = rows[y] if y < len(rows) else "." * len(rows[0])
            row_b = template[y] if y < len(template) else "." * len(template[0])
            row_a = row_a.ljust(width, ".")
            row_b = row_b.ljust(width, ".")
            score += sum(char_a != char_b for char_a, char_b in zip(row_a, row_b))
        if best_score is None or score < best_score:
            best_label = label
            best_score = score

    return best_label


def _find_actor_label(frame: bytes, actor_kind: str, actor_position: dict) -> str:
    candidates = []
    for box in _label_boxes(frame):
        label = _recognize_label(frame, box)
        if label and label.startswith(actor_kind):
            center_x = (box[0] + box[2]) / 2
            center_y = (box[1] + box[3]) / 2
            distance = math.dist((center_x, center_y), (actor_position["cx"], actor_position["cy"]))
            candidates.append((distance, label))

    if not candidates:
        raise AssertionError(f"Could not identify {actor_kind} label from frame")

    candidates.sort()
    return candidates[0][1]


def _select_near_miss(frames: list[bytes], pedestrian_tracks: list[list[dict]], moving_pedestrians: list[int]) -> tuple[int, dict, int]:
    forklift_detections = [_detect_forklifts(frame) for frame in frames]
    best_distance = None
    best_index = None
    best_forklift = None
    best_pedestrian_index = None

    for frame_index, forklifts in enumerate(forklift_detections):
        for pedestrian_index in moving_pedestrians:
            pedestrian = pedestrian_tracks[pedestrian_index][frame_index]
            for forklift in forklifts:
                distance = math.dist((forklift["cx"], forklift["cy"]), (pedestrian["cx"], pedestrian["cy"]))
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_index = frame_index
                    best_forklift = forklift
                    best_pedestrian_index = pedestrian_index

    if best_index is None or best_forklift is None or best_pedestrian_index is None:
        raise AssertionError("No near-miss candidate found in clip")

    return best_index, best_forklift, best_pedestrian_index


def _infer_summary(summary_codes: dict, pedestrian_track: list[dict], event_index: int) -> str:
    pre_dx = pedestrian_track[event_index]["cx"] - pedestrian_track[0]["cx"]
    pre_dy = pedestrian_track[event_index]["cy"] - pedestrian_track[0]["cy"]
    post_dx = pedestrian_track[-1]["cx"] - pedestrian_track[event_index]["cx"]
    post_dy = pedestrian_track[-1]["cy"] - pedestrian_track[event_index]["cy"]

    pre_axis = "x" if abs(pre_dx) >= abs(pre_dy) else "y"
    post_axis = "x" if abs(post_dx) >= abs(post_dy) else "y"
    pre_value = pre_dx if pre_axis == "x" else pre_dy
    post_value = post_dx if post_axis == "x" else post_dy

    if pre_axis == post_axis and pre_value and post_value and pre_value * post_value < 0:
        return summary_codes["reverse_conflict"]
    return summary_codes["crossing_conflict"]


def _timestamp(frame_index: int, fps: int) -> str:
    seconds = frame_index // fps
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _extract_actor_ids(setting: str) -> set[str]:
    return set(re.findall(r"\b[FP]\d+\b", setting))


@lru_cache(maxsize=1)
def _expected_payload() -> dict:
    policy = _load_policy(INPUT_DIR)
    summary_codes = policy["summary_codes"]
    clip_metadata = {item["filename"]: item for item in policy["clips"]}

    events = []
    clips_dir = INPUT_DIR / "clips"
    for video_path in sorted(clips_dir.glob("*.avi")):
        frames = _load_frames(video_path)
        fps = _read_fps(video_path)
        assert frames, f"No frames found in {video_path.name}"

        pedestrian_sequence = [_detect_pedestrians(frame) for frame in frames]
        assert len({len(items) for items in pedestrian_sequence}) == 1, f"Inconsistent pedestrian detections in {video_path.name}"

        pedestrian_tracks = _track_constant_count(pedestrian_sequence)
        moving_pedestrians = [
            index
            for index, track in enumerate(pedestrian_tracks)
            if math.dist((track[0]["cx"], track[0]["cy"]), (track[-1]["cx"], track[-1]["cy"])) > 12
        ]

        event_index, event_forklift, pedestrian_index = _select_near_miss(frames, pedestrian_tracks, moving_pedestrians)
        forklift_track = _trace_actor([_detect_forklifts(frame) for frame in frames], event_index, event_forklift)
        pedestrian_track = pedestrian_tracks[pedestrian_index]
        first_frame = frames[0]

        actor_ids = [
            _find_actor_label(first_frame, "F", forklift_track[0]),
            _find_actor_label(first_frame, "P", pedestrian_track[0]),
        ]
        allowed_ids = _extract_actor_ids(clip_metadata[video_path.name]["setting"])
        assert set(actor_ids).issubset(allowed_ids), f"Detected actor IDs {actor_ids} do not match clip roster for {video_path.name}"

        events.append(
            {
                "filename": video_path.name,
                "timestamp": _timestamp(event_index, fps),
                "actors": actor_ids,
                "summary": _infer_summary(summary_codes, pedestrian_track, event_index),
            }
        )

    events.sort(key=lambda item: (item["filename"], item["timestamp"], item["actors"][0], item["actors"][1]))
    return {"events": events}


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /app/output/near_miss_events.json"


def test_event_log_schema_and_values():
    payload = json.loads(OUTPUT_PATH.read_text())

    assert isinstance(payload, dict), "输出必须是 JSON object"
    assert set(payload.keys()) == {"events"}, "顶层字段必须且只能包含 events"

    events = payload["events"]
    assert isinstance(events, list), "events 必须是数组"

    for event in events:
        assert set(event.keys()) == {"filename", "timestamp", "actors", "summary"}, "每个事件对象只能包含 filename、timestamp、actors、summary"
        assert isinstance(event["filename"], str) and event["filename"], "filename 必须是非空字符串"
        assert TIMESTAMP_PATTERN.match(event["timestamp"]), "timestamp 必须是 MM:SS 格式"
        assert isinstance(event["actors"], list) and len(event["actors"]) == 2, "actors 必须是长度为 2 的数组"
        assert all(isinstance(actor, str) and actor for actor in event["actors"]), "actors 中的每个元素都必须是非空字符串"
        assert isinstance(event["summary"], str) and event["summary"], "summary 必须是非空字符串"

    assert events == _expected_payload()["events"], "events 内容必须按 filename 与 timestamp 升序给出所有满足阈值的险情"
