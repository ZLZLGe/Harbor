#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import os
import struct
from pathlib import Path


class Frame:
    def __init__(self, width: int, height: int, pixels: bytearray) -> None:
        self.width = width
        self.height = height
        self.pixels = pixels

    def rgb(self, x: int, y: int) -> tuple[int, int, int]:
        index = (y * self.width + x) * 3
        return tuple(self.pixels[index:index + 3])


def _iter_chunks(data: bytes, start: int, end: int):
    cursor = start
    while cursor + 8 <= end:
        fourcc = data[cursor:cursor + 4]
        size = struct.unpack_from("<I", data, cursor + 4)[0]
        payload_start = cursor + 8
        payload_end = payload_start + size
        yield fourcc, payload_start, payload_end
        cursor = payload_end + (size % 2)


def read_uncompressed_avi(path: Path) -> list[Frame]:
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"AVI ":
        raise ValueError(f"Unsupported video container: {path}")

    width: int | None = None
    height: int | None = None
    frames: list[Frame] = []

    for fourcc, payload_start, payload_end in _iter_chunks(data, 12, len(data)):
        if fourcc != b"LIST":
            continue

        list_type = data[payload_start:payload_start + 4]
        if list_type == b"hdrl":
            for inner_fourcc, inner_start, inner_end in _iter_chunks(data, payload_start + 4, payload_end):
                if inner_fourcc != b"LIST" or data[inner_start:inner_start + 4] != b"strl":
                    continue
                for leaf_fourcc, leaf_start, leaf_end in _iter_chunks(data, inner_start + 4, inner_end):
                    if leaf_fourcc == b"strf":
                        width = struct.unpack_from("<I", data, leaf_start + 4)[0]
                        height = struct.unpack_from("<I", data, leaf_start + 8)[0]
        elif list_type == b"movi":
            if width is None or height is None:
                raise ValueError(f"Missing stream format before movi list in {path}")
            row_stride = (width * 3 + 3) & ~3
            for inner_fourcc, inner_start, inner_end in _iter_chunks(data, payload_start + 4, payload_end):
                if inner_fourcc not in {b"00db", b"00dc"}:
                    continue
                raw = data[inner_start:inner_end]
                pixels = bytearray(width * height * 3)
                for y in range(height):
                    src_row = (height - 1 - y) * row_stride
                    for x in range(width):
                        b, g, r = raw[src_row + x * 3:src_row + x * 3 + 3]
                        dst = (y * width + x) * 3
                        pixels[dst:dst + 3] = bytes((r, g, b))
                frames.append(Frame(width, height, pixels))

    return frames


def detect_gauge_type(frame: Frame) -> str:
    cyan_score = 0
    red_score = 0
    for y in range(80, 165, 4):
        for x in range(70, 250, 4):
            r, g, b = frame.rgb(x, y)
            if g > 180 and b > 170 and r < 100:
                cyan_score += 1
            if r > 150 and g < 100 and b < 100:
                red_score += 1
    return "digital" if cyan_score > red_score else "analog"


def read_analog_value(frame: Frame) -> float:
    center_x = 160
    center_y = 150
    sum_x = 0.0
    sum_y = 0.0
    total_weight = 0.0

    for y in range(70, 170):
        for x in range(90, 230):
            r, g, b = frame.rgb(x, y)
            if not (r > 150 and g < 100 and b < 100):
                continue
            dx = x - center_x
            dy = center_y - y
            distance = math.hypot(dx, dy)
            if distance <= 12:
                continue
            sum_x += dx * distance
            sum_y += dy * distance
            total_weight += distance

    if total_weight == 0:
        raise ValueError("No pointer pixels detected")

    angle = math.degrees(math.atan2(sum_y / total_weight, sum_x / total_weight))
    return round((150.0 - angle) / 1.2, 1)


SEGMENT_MAP = {
    frozenset("abcedf"): "0",
    frozenset("bc"): "1",
    frozenset("abged"): "2",
    frozenset("abgcd"): "3",
    frozenset("fgbc"): "4",
    frozenset("afgcd"): "5",
    frozenset("afgecd"): "6",
    frozenset("abc"): "7",
    frozenset("abcdefg"): "8",
    frozenset("abcfgd"): "9",
}


def _segment_is_on(frame: Frame, x0: int, y0: int, x1: int, y1: int) -> bool:
    lit = 0
    total = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = frame.rgb(x, y)
            total += 1
            if g > 150 and b > 150 and r < 120:
                lit += 1
    return total > 0 and (lit / total) > 0.45


def read_digital_value(frame: Frame) -> float:
    digits: list[str] = []
    for origin_x in (74, 114, 154, 214):
        active = set()
        if _segment_is_on(frame, origin_x + 8, 92, origin_x + 32, 98):
            active.add("a")
        if _segment_is_on(frame, origin_x + 32, 98, origin_x + 38, 122):
            active.add("b")
        if _segment_is_on(frame, origin_x + 32, 128, origin_x + 38, 152):
            active.add("c")
        if _segment_is_on(frame, origin_x + 8, 152, origin_x + 32, 158):
            active.add("d")
        if _segment_is_on(frame, origin_x + 2, 128, origin_x + 8, 152):
            active.add("e")
        if _segment_is_on(frame, origin_x + 2, 98, origin_x + 8, 122):
            active.add("f")
        if _segment_is_on(frame, origin_x + 8, 122, origin_x + 32, 128):
            active.add("g")
        digits.append(SEGMENT_MAP[frozenset(active)])

    return float("".join(digits[:-1]) + "." + digits[-1])


def read_frame_value(frame: Frame) -> float:
    gauge_type = detect_gauge_type(frame)
    if gauge_type == "digital":
        return read_digital_value(frame)
    return read_analog_value(frame)


def solve(input_dir: Path, output_path: Path) -> None:
    video_files = sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".avi")
    rows: list[dict[str, str]] = []

    for video_path in video_files:
        frames = read_uncompressed_avi(video_path)
        readings = [read_frame_value(frame) for frame in frames]
        peak_value = max(readings)
        peak_index = readings.index(peak_value)
        rows.append(
            {
                "video_filename": video_path.name,
                "peak_frame_id": f"F{peak_index:04d}",
                "max_reading": f"{peak_value:.1f}",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["video_filename", "peak_frame_id", "max_reading"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    input_dir = Path(os.environ.get("INPUT_DIR", "/app/inspection/videos"))
    output_path = Path(os.environ.get("OUTPUT_FILE", "/app/inspection/gauge_maxima.csv"))
    solve(input_dir, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
