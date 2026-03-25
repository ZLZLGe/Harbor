#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import csv
import json
import struct
import zlib
from pathlib import Path

import numpy as np


INPUT_DIR = Path("/app/input")
OUTPUT_PATH = Path("/app/output/shelf_audit.csv")


def read_png(path: Path) -> np.ndarray:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"Unsupported PNG header: {path}"

    pos = 8
    width = height = None
    idat_parts = []

    while pos < len(data):
        length = struct.unpack("!I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, flt, interlace = struct.unpack(
                "!IIBBBBB", chunk_data
            )
            assert bit_depth == 8 and color_type == 2 and compression == 0 and flt == 0 and interlace == 0
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * 3
    image = np.zeros((height, width, 3), dtype=np.uint8)
    offset = 0

    for row_idx in range(height):
        filter_type = raw[offset]
        offset += 1
        row_bytes = bytearray(raw[offset:offset + stride])
        offset += stride

        if filter_type == 1:
            for i in range(stride):
                left = row_bytes[i - 3] if i >= 3 else 0
                row_bytes[i] = (row_bytes[i] + left) & 0xFF
        elif filter_type == 2:
            prev = image[row_idx - 1].reshape(-1) if row_idx > 0 else np.zeros(stride, dtype=np.uint8)
            for i in range(stride):
                row_bytes[i] = (row_bytes[i] + int(prev[i])) & 0xFF
        elif filter_type == 3:
            prev = image[row_idx - 1].reshape(-1) if row_idx > 0 else np.zeros(stride, dtype=np.uint8)
            for i in range(stride):
                left = row_bytes[i - 3] if i >= 3 else 0
                row_bytes[i] = (row_bytes[i] + ((left + int(prev[i])) // 2)) & 0xFF
        elif filter_type == 4:
            prev = image[row_idx - 1].reshape(-1) if row_idx > 0 else np.zeros(stride, dtype=np.uint8)

            def paeth(a: int, b: int, c: int) -> int:
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                if pa <= pb and pa <= pc:
                    return a
                if pb <= pc:
                    return b
                return c

            for i in range(stride):
                left = row_bytes[i - 3] if i >= 3 else 0
                up = int(prev[i])
                up_left = int(prev[i - 3]) if i >= 3 else 0
                row_bytes[i] = (row_bytes[i] + paeth(left, up, up_left)) & 0xFF
        else:
            assert filter_type == 0, f"Unsupported PNG filter {filter_type} in {path}"

        image[row_idx] = np.frombuffer(bytes(row_bytes), dtype=np.uint8).reshape(width, 3)

    return image


def count_components(mask: np.ndarray) -> int:
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    count = 0

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue

            stack = [(y, x)]
            visited[y, x] = True
            area = 0

            while stack:
                cy, cx = stack.pop()
                area += 1
                if cy > 0 and mask[cy - 1, cx] and not visited[cy - 1, cx]:
                    visited[cy - 1, cx] = True
                    stack.append((cy - 1, cx))
                if cy + 1 < height and mask[cy + 1, cx] and not visited[cy + 1, cx]:
                    visited[cy + 1, cx] = True
                    stack.append((cy + 1, cx))
                if cx > 0 and mask[cy, cx - 1] and not visited[cy, cx - 1]:
                    visited[cy, cx - 1] = True
                    stack.append((cy, cx - 1))
                if cx + 1 < width and mask[cy, cx + 1] and not visited[cy, cx + 1]:
                    visited[cy, cx + 1] = True
                    stack.append((cy, cx + 1))

            if area >= 12000:
                count += 1

    return count


with (INPUT_DIR / "product_reference.json").open("r", encoding="utf-8") as f:
    reference_rows = json.load(f)

rgb_by_code = {row["package_code"]: tuple(row["rgb"]) for row in reference_rows}

with (INPUT_DIR / "audit_targets.csv").open("r", encoding="utf-8", newline="") as f:
    targets = list(csv.DictReader(f))

images = {}
for row in targets:
    photo_id = row["photo_id"]
    if photo_id not in images:
        images[photo_id] = read_png(INPUT_DIR / "photos" / f"{photo_id}.png")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["photo_id", "product_name", "target_facings", "visible_facings", "audit_status"])

    for row in targets:
        photo_id = row["photo_id"]
        target = int(row["target_facings"])
        rgb = rgb_by_code[row["package_code"]]
        mask = np.all(images[photo_id] == np.array(rgb, dtype=np.uint8), axis=2)
        visible = count_components(mask)

        if visible == 0:
            status = "out_of_stock"
        elif visible < target:
            status = "understocked"
        else:
            status = "ok"

        writer.writerow([photo_id, row["product_name"], target, visible, status])
PY
