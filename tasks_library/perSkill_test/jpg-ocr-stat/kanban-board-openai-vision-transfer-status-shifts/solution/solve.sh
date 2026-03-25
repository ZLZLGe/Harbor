#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import json
import struct
import zlib
from pathlib import Path

OUTPUT_PATH = Path("/app/workspace/kanban_status_diff.ndjson")
MORNING_PATH = Path("/app/workspace/board_snapshots/board_morning.png")
EVENING_PATH = Path("/app/workspace/board_snapshots/board_evening.png")

COLUMNS = ["Queued", "Building", "Review", "Shipped"]
LEFT = 28
TOP = 32
COL_W = 229
COL_GAP = 18
HEADER_H = 70
SLOT_H = 146
ROW_GAP = 18
CARD_INSET_X = 8
CARD_INSET_Y = 9

FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "01010", "00100", "00100", "00100", "01010", "10001"],
    "Y": ["10001", "01010", "00100", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}
FONT_BY_PATTERN = {tuple(pattern): char for char, pattern in FONT.items()}


def read_png(path: Path) -> list[list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")

    pos = 8
    width = 0
    height = 0
    idat = bytearray()

    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += length + 12

        if tag == b"IHDR":
            width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", chunk)
            if (bit_depth, color_type, comp, filt, interlace) != (8, 2, 0, 0, 0):
                raise ValueError("Unsupported PNG format")
        elif tag == b"IDAT":
            idat.extend(chunk)
        elif tag == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    stride = width * 3
    cursor = 0
    rows: list[list[tuple[int, int, int]]] = []

    for _ in range(height):
        filter_type = raw[cursor]
        if filter_type != 0:
            raise ValueError("Unsupported PNG filter type")
        cursor += 1
        row_bytes = raw[cursor : cursor + stride]
        cursor += stride
        row = [tuple(row_bytes[i : i + 3]) for i in range(0, stride, 3)]
        rows.append(row)

    return rows


def is_dark(pixel: tuple[int, int, int]) -> bool:
    return sum(pixel) < 220


def decode_title(image: list[list[tuple[int, int, int]]], slot_x: int, slot_y: int) -> str:
    card_x = slot_x + CARD_INSET_X
    card_y = slot_y + CARD_INSET_Y
    text_x = card_x + 18
    text_y = card_y + 54

    chars: list[str] = []
    for char_index in range(13):
        char_left = text_x + char_index * 12
        pattern: list[str] = []
        for glyph_y in range(7):
            bits: list[str] = []
            for glyph_x in range(5):
                sample_x = char_left + glyph_x * 2 + 1
                sample_y = text_y + glyph_y * 2 + 1
                bits.append("1" if is_dark(image[sample_y][sample_x]) else "0")
            pattern.append("".join(bits))
        chars.append(FONT_BY_PATTERN.get(tuple(pattern), ""))

    return "".join(chars).rstrip()


def parse_board(path: Path) -> dict[str, str]:
    image = read_png(path)
    positions: dict[str, str] = {}

    for column_index, column_name in enumerate(COLUMNS):
        column_left = LEFT + column_index * (COL_W + COL_GAP)
        slot_left = column_left + 16

        for row_index in range(3):
            slot_top = TOP + HEADER_H + 18 + row_index * (SLOT_H + ROW_GAP)
            card_left = slot_left + CARD_INSET_X
            card_top = slot_top + CARD_INSET_Y

            sample = image[card_top + 20][card_left + 20]
            if sum(sample) <= 740:
                continue

            title = decode_title(image, slot_left, slot_top)
            if not title:
                continue
            positions[title] = column_name

    return positions


morning = parse_board(MORNING_PATH)
evening = parse_board(EVENING_PATH)

records = []
for card_text in sorted(set(morning) | set(evening)):
    from_column = morning.get(card_text, "")
    to_column = evening.get(card_text, "")

    if from_column and to_column:
        change_type = "unchanged" if from_column == to_column else "moved"
    elif to_column:
        change_type = "new_card"
    else:
        change_type = "removed_card"

    records.append(
        {
            "card_text": card_text,
            "from_column": from_column,
            "to_column": to_column,
            "change_type": change_type,
        }
    )

OUTPUT_PATH.write_text(
    "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
    encoding="utf-8",
)
PY
