#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import json
import struct
import zlib
from pathlib import Path


IMAGE_DIR = Path("/app/workspace/parking_surveillance")
OUTPUT_FILE = Path("/app/workspace/parking_occupancy.json")
ZONE_TOPS = {"north": 60, "center": 280, "south": 500}
LEFT = 80
SLOT_WIDTH = 150
SLOT_GAP = 10
SLOT_TOP_OFFSET = 20
INNER_BOX = (44, 28, 106, 72)


def load_png_rgb(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")

    width = height = None
    idat_chunks = bytearray()
    offset = 8
    while offset < len(data):
        length = struct.unpack("!I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                "!IIBBBBB", chunk_data
            )
            if (bit_depth, color_type, compression, filter_method, interlace) != (8, 2, 0, 0, 0):
                raise ValueError("Unsupported PNG encoding")
        elif chunk_type == b"IDAT":
            idat_chunks.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError("Missing PNG header")

    raw = zlib.decompress(bytes(idat_chunks))
    stride = width * 3
    rows = bytearray()
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        if filter_type != 0:
            raise ValueError("Unsupported PNG filter")
        rows.extend(raw[cursor : cursor + stride])
        cursor += stride

    return width, height, bytes(rows)


def count_colorful_pixels(width: int, rgb: bytes, box: tuple[int, int, int, int]) -> int:
    x0, y0, x1, y1 = box
    colorful = 0
    for y in range(y0, y1):
        row_offset = y * width * 3
        for x in range(x0, x1):
            idx = row_offset + x * 3
            r, g, b = rgb[idx], rgb[idx + 1], rgb[idx + 2]
            spread = max(r, g, b) - min(r, g, b)
            if spread >= 18 and max(r, g, b) >= 90:
                colorful += 1
    return colorful


def slot_is_occupied(width: int, rgb: bytes, slot_x: int, slot_y: int) -> bool:
    inner = (
        slot_x + INNER_BOX[0],
        slot_y + INNER_BOX[1],
        slot_x + INNER_BOX[2],
        slot_y + INNER_BOX[3],
    )
    colorful = count_colorful_pixels(width, rgb, inner)
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return colorful > area * 0.18


captures = []
for image_path in sorted(IMAGE_DIR.glob("*.png")):
    width, _, rgb = load_png_rgb(image_path)
    zone_counts = {}
    total = 0
    for zone_name, zone_top in ZONE_TOPS.items():
        slot_y = zone_top + SLOT_TOP_OFFSET
        count = 0
        for slot_index in range(5):
            slot_x = LEFT + slot_index * (SLOT_WIDTH + SLOT_GAP)
            if slot_is_occupied(width, rgb, slot_x, slot_y):
                count += 1
        zone_counts[zone_name] = count
        total += count
    captures.append(
        {
            "timepoint": image_path.stem,
            "zone_counts": zone_counts,
            "total_occupied": total,
        }
    )

peak_total = max(capture["total_occupied"] for capture in captures)
peak_timepoints = [capture["timepoint"] for capture in captures if capture["total_occupied"] == peak_total]

OUTPUT_FILE.write_text(
    json.dumps(
        {
            "captures": captures,
            "peak_timepoints": peak_timepoints,
            "peak_total_occupied": peak_total,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
