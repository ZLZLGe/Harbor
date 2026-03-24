from __future__ import annotations

import csv
import math
import os
import struct
from pathlib import Path


VIDEO_DIR = Path("/app/inspection/videos")
OUTPUT_FILE = Path("/app/inspection/gauge_maxima.csv")
REWARD_FILE = Path("/logs/verifier/reward.txt")


class Frame:
    def __init__(self, width: int, height: int, pixels: bytearray) -> None:
        self.width = width
        self.height = height
        self.pixels = pixels

    def rgb(self, x: int, y: int) -> tuple[int, int, int]:
        index = (y * self.width + x) * 3
        return tuple(self.pixels[index:index + 3])


def _write_reward(value: float) -> None:
    REWARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    REWARD_FILE.write_text(f"{value:.6f}\n", encoding="utf-8")


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
    assert data[:4] == b"RIFF" and data[8:12] == b"AVI ", f"Unsupported video: {path}"

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
            assert width is not None and height is not None, f"Missing video dimensions in {path}"
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

    assert total_weight > 0, "No pointer pixels detected"
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
    return read_digital_value(frame) if detect_gauge_type(frame) == "digital" else read_analog_value(frame)


def build_expected_rows() -> list[list[str]]:
    rows = [["video_filename", "peak_frame_id", "max_reading"]]
    for video_path in sorted(VIDEO_DIR.glob("*.avi")):
        frames = read_uncompressed_avi(video_path)
        readings = [read_frame_value(frame) for frame in frames]
        peak_value = max(readings)
        peak_index = readings.index(peak_value)
        rows.append([video_path.name, f"F{peak_index:04d}", f"{peak_value:.1f}"])
    return rows


def load_actual_rows() -> list[list[str]]:
    with OUTPUT_FILE.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def score_rows(actual_rows: list[list[str]], expected_rows: list[list[str]]) -> float:
    actual_map = {
        row[0]: row[1:]
        for row in actual_rows[1:]
        if len(row) == 3 and row[0].strip()
    }
    total = 0.0
    for video_filename, expected_frame, expected_reading in expected_rows[1:]:
        actual_frame, actual_reading = actual_map.get(video_filename, ["", ""])
        frame_reward = 1.0 if actual_frame == expected_frame else 0.0
        try:
            diff = abs(float(actual_reading) - float(expected_reading))
            reading_reward = 1.0 / (1.0 + diff)
        except ValueError:
            reading_reward = 0.0
        row_reward = 0.6 * frame_reward + 0.4 * reading_reward
        total += row_reward
        print(
            f"{video_filename}: frame {actual_frame} vs {expected_frame}, "
            f"reading {actual_reading} vs {expected_reading}, reward={row_reward:.4f}"
        )
    return total / max(1, len(expected_rows) - 1)


def test_outputs() -> None:
    if not OUTPUT_FILE.exists():
        _write_reward(0.0)
        raise AssertionError("gauge_maxima.csv not found at /app/inspection")

    expected_rows = build_expected_rows()

    try:
        actual_rows = load_actual_rows()

        print("\nExpected rows:")
        for row in expected_rows:
            print(row)

        print("\nActual rows:")
        for row in actual_rows:
            print(row)

        assert actual_rows, "CSV output is empty"
        assert actual_rows[0] == expected_rows[0], f"Header mismatch: {actual_rows[0]}"

        non_empty_rows = [row for row in actual_rows if any(cell.strip() for cell in row)]
        assert len(non_empty_rows) == len(expected_rows), (
            f"Expected {len(expected_rows)} non-empty rows, got {len(non_empty_rows)}"
        )

        for row in actual_rows[1:]:
            assert len(row) == 3, f"Each data row must have exactly 3 columns, got {row}"
            assert row[1].startswith("F") and row[1][1:].isdigit() and len(row[1]) == 5, (
                f"Invalid peak_frame_id format: {row[1]}"
            )

        _write_reward(score_rows(actual_rows, expected_rows))

        assert actual_rows == expected_rows, (
            "CSV content mismatch.\n"
            f"Actual:   {actual_rows}\n"
            f"Expected: {expected_rows}"
        )
    except Exception:
        try:
            actual_rows = load_actual_rows()
            _write_reward(score_rows(actual_rows, expected_rows))
        except Exception:
            _write_reward(0.0)
        raise
