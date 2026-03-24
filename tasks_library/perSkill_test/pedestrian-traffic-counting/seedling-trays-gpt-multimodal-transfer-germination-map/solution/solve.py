#!/usr/bin/env python3

import csv
import struct
import zlib
from pathlib import Path

import numpy as np


IMAGE_DIR = Path("/app/trays/images")
OUTPUT_PATH = Path("/app/trays/germination_report.csv")
ROWS = "ABCDE"
COLS = range(1, 9)
GRID_X = 300
GRID_Y = 220
CELL_W = 145
CELL_H = 145
GAP_X = 20
GAP_Y = 22


def read_png(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"unsupported image format: {path}")

    pos = 8
    idat = b""
    width = 0
    height = 0

    while pos < len(data):
        length = struct.unpack("!I", data[pos:pos + 4])[0]
        pos += 4
        tag = data[pos:pos + 4]
        pos += 4
        chunk = data[pos:pos + length]
        pos += length
        pos += 4

        if tag == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack("!IIBBBBB", chunk)
            if bit_depth != 8 or color_type != 2:
                raise ValueError(f"unsupported PNG encoding: {path}")
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break

    raw = zlib.decompress(idat)
    stride = width * 3
    image = np.zeros((height, width, 3), dtype=np.uint8)
    cursor = 0

    for row_index in range(height):
        filter_type = raw[cursor]
        cursor += 1
        if filter_type != 0:
            raise ValueError(f"unsupported PNG filter type {filter_type} in {path}")
        row = np.frombuffer(raw[cursor:cursor + stride], dtype=np.uint8)
        image[row_index] = row.reshape((width, 3))
        cursor += stride

    return image


def cell_crop(image: np.ndarray, row_index: int, col_index: int) -> np.ndarray:
    x0 = GRID_X + col_index * (CELL_W + GAP_X)
    y0 = GRID_Y + row_index * (CELL_H + GAP_Y)
    return image[y0 + 45:y0 + 110, x0 + 40:x0 + 105]


def is_germinated(crop: np.ndarray) -> bool:
    green_mask = (
        (crop[:, :, 1] > 130)
        & (crop[:, :, 1] > crop[:, :, 0] + 25)
        & (crop[:, :, 1] > crop[:, :, 2] + 20)
    )
    return int(green_mask.sum()) > 200


def detect_cells(image_path: Path) -> list[str]:
    image = read_png(image_path)
    cells: list[str] = []
    for row_index, row_label in enumerate(ROWS):
        for col_index, col_label in enumerate(COLS):
            if is_germinated(cell_crop(image, row_index, col_index)):
                cells.append(f"{row_label}{col_label}")
    return cells


def main() -> int:
    image_paths = sorted(IMAGE_DIR.glob("*.png"))
    rows: list[list[str]] = [["tray_id", "germinated_count", "germinated_cells"]]

    for image_path in image_paths:
        cells = detect_cells(image_path)
        rows.append([
            image_path.stem,
            str(len(cells)),
            ";".join(cells),
        ])

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
