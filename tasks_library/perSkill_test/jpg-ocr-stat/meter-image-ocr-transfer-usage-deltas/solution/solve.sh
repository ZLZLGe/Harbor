#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import struct
import zlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path


WORKSPACE_DIR = Path(__import__("os").environ.get("WORKSPACE_DIR", "/app/workspace"))
INPUT_DIR = WORKSPACE_DIR / "meter_photos"
OUTPUT_FILE = WORKSPACE_DIR / "meter_consumption.json"

FONT = {
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", "..##.", "..##."],
    "/": ["....#", "...#.", "..#..", ".#...", "#....", ".....", "....."],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "#....", "####.", "....#", "....#", "####."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
}

REV_FONT = {tuple(pattern): char for char, pattern in FONT.items()}
SCALE = 12
CELL_W = 6 * SCALE
X0 = 72
Y0 = 70
LINE_STEP = 7 * SCALE + 48


def read_png(path: Path) -> tuple[int, int, list[bytes]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} is not a PNG file")

    position = 8
    width = height = None
    compressed = bytearray()

    while position < len(data):
        chunk_length = struct.unpack(">I", data[position : position + 4])[0]
        position += 4
        chunk_type = data[position : position + 4]
        position += 4
        chunk_data = data[position : position + chunk_length]
        position += chunk_length + 4

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
            if bit_depth != 8 or color_type != 2:
                raise ValueError(f"unsupported PNG format in {path.name}")
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError(f"broken PNG header in {path.name}")

    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    rows = []
    cursor = 0
    for _ in range(height):
        if raw[cursor] != 0:
            raise ValueError(f"unsupported PNG filter in {path.name}")
        cursor += 1
        rows.append(raw[cursor : cursor + stride])
        cursor += stride
    return width, height, rows


def pixel_is_dark(rows: list[bytes], x: int, y: int) -> bool:
    pixel = rows[y][x * 3 : (x + 1) * 3]
    return sum(pixel) < 300


def decode_line(rows: list[bytes], line_index: int) -> str:
    base_y = Y0 + line_index * LINE_STEP
    characters = []
    started = False
    empty_cells = 0

    for cell_index in range(24):
        base_x = X0 + cell_index * CELL_W
        glyph = []
        has_ink = False
        for gy in range(7):
            row_pattern = []
            for gx in range(5):
                sample_x = base_x + gx * SCALE + SCALE // 2
                sample_y = base_y + gy * SCALE + SCALE // 2
                dark = pixel_is_dark(rows, sample_x, sample_y)
                row_pattern.append("#" if dark else ".")
                has_ink = has_ink or dark
            glyph.append("".join(row_pattern))

        if not has_ink:
            if started:
                empty_cells += 1
                if empty_cells >= 2:
                    break
            continue

        started = True
        empty_cells = 0
        characters.append(REV_FONT[tuple(glyph)])

    return "".join(characters)


def normalize_date(raw: str) -> str:
    value = raw.replace("DATE", "", 1)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {raw}")


def normalize_reading(raw: str) -> str:
    match = re.search(r"READ([0-9]+\.[0-9])M3", raw)
    if not match:
        raise ValueError(f"unrecognized reading: {raw}")
    return f"{Decimal(match.group(1)):.1f}"


entries = []
for image_path in sorted(INPUT_DIR.glob("*.png")):
    _, _, rows = read_png(image_path)
    date_text = decode_line(rows, 1)
    reading_text = decode_line(rows, 2)
    entries.append(
        {
            "filename": image_path.name,
            "date": normalize_date(date_text),
            "reading": normalize_reading(reading_text),
        }
    )

entries.sort(key=lambda item: item["date"])

previous = None
for item in entries:
    current = Decimal(item["reading"])
    if previous is None:
        item["delta_from_previous"] = None
    else:
        item["delta_from_previous"] = f"{(current - previous):.1f}"
    previous = current

total = Decimal(entries[-1]["reading"]) - Decimal(entries[0]["reading"])
payload = {
    "readings": entries,
    "total_consumption": f"{total:.1f}",
}

OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
