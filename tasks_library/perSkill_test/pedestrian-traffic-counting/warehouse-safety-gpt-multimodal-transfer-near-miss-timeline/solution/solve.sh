#!/bin/bash

python3 - <<'PY'
import json
import math
import struct
import zlib
from pathlib import Path

INPUT_DIR = Path("/app/input")
OUTPUT_PATH = Path("/app/output/near_miss_timeline.json")
FORKLIFT_COLOR = (234, 124, 33)
PERSON_COLOR = (48, 93, 178)
DISTANCE_THRESHOLD = 34.0


def read_png_rgb(path: Path) -> list[list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unsupported PNG header: {path}")

    pos = 8
    width = height = None
    bit_depth = color_type = None
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
            if (bit_depth, color_type, compression, filter_method, interlace) != (8, 2, 0, 0, 0):
                raise ValueError(f"Unsupported PNG format in {path}")
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError(f"Missing IHDR in {path}")

    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    rows = []
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        if filter_type != 0:
            raise ValueError(f"Unsupported PNG filter {filter_type} in {path}")
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


def analyze_clip(clip: dict, zones: list[dict]) -> dict:
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
                    person_zone = point_in_zone(person, zones)
                    if person_zone == forklift_zone:
                        distance = math.dist(forklift, person)
                        if distance <= DISTANCE_THRESHOLD:
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

    return {
        "video_id": clip["video_id"],
        "event_count": len(events),
        "events": events,
    }


def main() -> None:
    manifest = json.loads((INPUT_DIR / "clip_manifest.json").read_text(encoding="utf-8"))
    zone_reference = json.loads((INPUT_DIR / "zone_reference.json").read_text(encoding="utf-8"))
    zones = zone_reference["warning_zones"]

    result = {"videos": [analyze_clip(clip, zones) for clip in manifest["videos"]]}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
