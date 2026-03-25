#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import csv
import struct
import zlib
from pathlib import Path

START_DIR = Path("/app/workspace/field_capture/period_start")
END_DIR = Path("/app/workspace/field_capture/period_end")
OUTPUT_FILE = Path("/app/workspace/meter_usage.csv")

DIGIT_X = 225
DIGIT_Y = 185
DIGIT_STEP = 78
SEGMENTS = {
    "a": (12, 0, 58, 10),
    "b": (60, 10, 70, 56),
    "c": (60, 64, 70, 110),
    "d": (12, 110, 58, 120),
    "e": (0, 64, 10, 110),
    "f": (0, 10, 10, 56),
    "g": (12, 55, 58, 65),
}
SEGMENT_TO_DIGIT = {
    frozenset("abcdef"): "0",
    frozenset("bc"): "1",
    frozenset("abdeg"): "2",
    frozenset("abcdg"): "3",
    frozenset("bcfg"): "4",
    frozenset("acdfg"): "5",
    frozenset("acdefg"): "6",
    frozenset("abc"): "7",
    frozenset("abcdefg"): "8",
    frozenset("abcdfg"): "9",
}


def read_png(path: Path) -> tuple[int, int, list[bytes]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")

    pos = 8
    width = 0
    height = 0
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        tag = data[pos:pos + 4]
        pos += 4
        chunk = data[pos:pos + length]
        pos += length + 4
        if tag == b"IHDR":
            width, height, bit_depth, color_type, _, filter_method, interlace = struct.unpack(">IIBBBBB", chunk)
            if (bit_depth, color_type, filter_method, interlace) != (8, 2, 0, 0):
                raise ValueError(f"{path} uses an unsupported PNG variant")
        elif tag == b"IDAT":
            idat.extend(chunk)
        elif tag == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    row_bytes = width * 3
    rows: list[bytes] = []
    idx = 0
    for _ in range(height):
        filter_type = raw[idx]
        idx += 1
        if filter_type != 0:
            raise ValueError(f"{path} uses unsupported PNG filter {filter_type}")
        rows.append(raw[idx:idx + row_bytes])
        idx += row_bytes
    return width, height, rows


def mean_gray(rows: list[bytes], x0: int, y0: int, x1: int, y1: int) -> float:
    total = 0
    count = 0
    for y in range(y0, y1):
        row = rows[y]
        for x in range(x0, x1):
            idx = x * 3
            total += row[idx] + row[idx + 1] + row[idx + 2]
            count += 3
    return total / count


def decode_reading(path: Path) -> str:
    _, _, rows = read_png(path)
    digits: list[str] = []
    for digit_idx in range(6):
        box_x = DIGIT_X + digit_idx * DIGIT_STEP
        box_y = DIGIT_Y
        active_segments = []
        for name, (sx0, sy0, sx1, sy1) in SEGMENTS.items():
            if mean_gray(rows, box_x + sx0, box_y + sy0, box_x + sx1, box_y + sy1) < 120:
                active_segments.append(name)
        key = frozenset(active_segments)
        if key not in SEGMENT_TO_DIGIT:
            raise ValueError(f"Could not decode digit {digit_idx} from {path.name}: {sorted(active_segments)}")
        digits.append(SEGMENT_TO_DIGIT[key])
    return "".join(digits)


start_files = {path.stem: path for path in START_DIR.glob("*.png")}
end_files = {path.stem: path for path in END_DIR.glob("*.png")}
if set(start_files) != set(end_files):
    raise ValueError("Start and end directories do not contain the same meter IDs")

rows_to_write: list[list[str]] = []
for meter_id in sorted(start_files):
    start_reading = decode_reading(start_files[meter_id])
    end_reading = decode_reading(end_files[meter_id])
    consumption = str(int(end_reading) - int(start_reading))
    rows_to_write.append([meter_id, start_reading, end_reading, consumption])

with OUTPUT_FILE.open("w", newline="") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["meter_id", "start_reading", "end_reading", "consumption"])
    writer.writerows(rows_to_write)
PY
