import json
import math
import re
import struct
import zlib
from pathlib import Path


OUTPUT_PATH = Path("/app/output/near_miss_timeline.json")
MANIFEST_PATH = Path("/app/input/clip_manifest.json")
ZONE_REFERENCE_PATH = Path("/app/input/zone_reference.json")
INPUT_DIR = Path("/app/input")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
FORKLIFT_COLOR = (234, 124, 33)
PERSON_COLOR = (48, 93, 178)
DISTANCE_THRESHOLD = 34.0


def parse_time(value: str) -> int:
    assert TIME_RE.match(value), f"时间格式错误: {value}"
    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def read_png_rgb(path: Path) -> list[list[tuple[int, int, int]]]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"无法读取 PNG 文件: {path}"

    pos = 8
    width = height = None
    compressed = bytearray()

    while pos < len(data):
        length = struct.unpack("!I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                "!IIBBBBB", chunk_data
            )
            assert (bit_depth, color_type, compression, filter_method, interlace) == (8, 2, 0, 0, 0), (
                f"不支持的 PNG 格式: {path}"
            )
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    assert width is not None and height is not None, f"PNG 缺少 IHDR: {path}"

    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    rows = []
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        assert filter_type == 0, f"不支持的 PNG filter 类型: {filter_type}"
        offset += 1
        row_bytes = raw[offset:offset + stride]
        offset += stride
        row = []
        for i in range(0, len(row_bytes), 3):
            row.append((row_bytes[i], row_bytes[i + 1], row_bytes[i + 2]))
        rows.append(row)
    return rows


def find_components(image: list[list[tuple[int, int, int]]], target: tuple[int, int, int]) -> list[tuple[float, float]]:
    height = len(image)
    width = len(image[0])
    visited = [[False] * width for _ in range(height)]
    centers = []

    for y in range(height):
        for x in range(width):
            if visited[y][x] or image[y][x] != target:
                continue

            queue = [(x, y)]
            visited[y][x] = True
            pixels = []

            while queue:
                cx, cy = queue.pop()
                pixels.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx] and image[ny][nx] == target:
                        visited[ny][nx] = True
                        queue.append((nx, ny))

            if len(pixels) < 8:
                continue
            avg_x = sum(px for px, _ in pixels) / len(pixels)
            avg_y = sum(py for _, py in pixels) / len(pixels)
            centers.append((avg_x, avg_y))

    return centers


def point_in_zone(point: tuple[float, float], zones: list[dict]) -> str | None:
    x, y = point
    for zone in zones:
        x1, y1, x2, y2 = zone["bbox"]
        if x1 <= x <= x2 and y1 <= y <= y2:
            return zone["zone_id"]
    return None


def second_to_mmss(second: int) -> str:
    return f"{second // 60:02d}:{second % 60:02d}"


def derive_events(clip: dict, zones: list[dict]) -> list[dict]:
    frame_dir = INPUT_DIR / clip["frame_dir"]
    frame_paths = sorted(frame_dir.glob("frame_*.png"))
    active_zone = None
    active_start = None
    events = []

    for second, frame_path in enumerate(frame_paths):
        image = read_png_rgb(frame_path)
        forklifts = find_components(image, FORKLIFT_COLOR)
        people = find_components(image, PERSON_COLOR)

        frame_zone = None
        if forklifts:
            forklift = forklifts[0]
            forklift_zone = point_in_zone(forklift, zones)
            if forklift_zone:
                for person in people:
                    if point_in_zone(person, zones) != forklift_zone:
                        continue
                    if math.dist(forklift, person) <= DISTANCE_THRESHOLD:
                        frame_zone = forklift_zone
                        break

        if frame_zone == active_zone and active_zone is not None:
            continue

        if active_zone is not None:
            events.append(
                {
                    "event_index": len(events) + 1,
                    "zone_id": active_zone,
                    "start_time": second_to_mmss(active_start),
                    "end_time": second_to_mmss(second - 1),
                }
            )
            active_zone = None
            active_start = None

        if frame_zone is not None:
            active_zone = frame_zone
            active_start = second

    if active_zone is not None:
        events.append(
            {
                "event_index": len(events) + 1,
                "zone_id": active_zone,
                "start_time": second_to_mmss(active_start),
                "end_time": second_to_mmss(len(frame_paths) - 1),
            }
        )

    return events


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /app/output/near_miss_timeline.json"


def test_json_contract_and_values():
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    zone_reference = json.loads(ZONE_REFERENCE_PATH.read_text(encoding="utf-8"))
    durations = {item["video_id"]: item["duration_seconds"] for item in manifest["videos"]}
    expected_order = [item["video_id"] for item in manifest["videos"]]
    derived_events = {
        clip["video_id"]: derive_events(clip, zone_reference["warning_zones"])
        for clip in manifest["videos"]
    }

    assert isinstance(data, dict), "输出必须是 JSON 对象"
    assert set(data.keys()) == {"videos"}, "顶层只能包含 videos"

    videos = data["videos"]
    assert isinstance(videos, list), "videos 必须是数组"
    assert len(videos) == len(expected_order), f"videos 必须包含 {len(expected_order)} 条记录"

    actual_order = []
    for video in videos:
        assert isinstance(video, dict), "videos 中的每一项都必须是对象"
        assert set(video.keys()) == {"video_id", "event_count", "events"}, (
            "每个视频对象只能包含 video_id、event_count、events"
        )

        video_id = video["video_id"]
        actual_order.append(video_id)
        assert video_id in derived_events, f"未知 video_id: {video_id}"
        assert isinstance(video["event_count"], int), f"{video_id}.event_count 必须是整数"
        assert isinstance(video["events"], list), f"{video_id}.events 必须是数组"
        assert video["event_count"] == len(video["events"]), (
            f"{video_id}.event_count 必须等于 events 长度"
        )
        assert video["events"] == derived_events[video_id], f"{video_id} 的事件时间线与输入帧不一致"

        previous_end = -1
        for expected_index, event in enumerate(video["events"], start=1):
            assert set(event.keys()) == {"event_index", "zone_id", "start_time", "end_time"}, (
                "每个事件对象只能包含 event_index、zone_id、start_time、end_time"
            )
            assert event["event_index"] == expected_index, f"{video_id} 的 event_index 必须连续递增"
            assert event["zone_id"] in {"Z1", "Z2", "Z3"}, f"{video_id} 存在非法 zone_id: {event['zone_id']}"

            start_second = parse_time(event["start_time"])
            end_second = parse_time(event["end_time"])
            assert start_second <= end_second, f"{video_id} 存在 start_time 晚于 end_time 的事件"
            assert end_second < durations[video_id], f"{video_id} 的事件时间超出片段时长"
            assert start_second > previous_end, f"{video_id} 的事件时间段不应重叠或倒序"
            previous_end = end_second

    assert actual_order == expected_order, "videos 顺序错误，必须与 clip_manifest.json 一致"
