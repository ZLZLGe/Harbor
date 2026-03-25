#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import struct
import zlib
from pathlib import Path


INPUT_DIR = Path("/app/workspace/arena_scoreboards")
OUTPUT_PATH = Path("/app/workspace/scoreboard_rankings.csv")

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
}

TEAM_CANDIDATES = ["COBRAS", "FALCONS", "LYNX", "ORBITS"]
LETTER_KEYS = [key for key in FONT if key.isalpha()]
DIGIT_KEYS = [key for key in FONT if key.isdigit()]


def read_png(path: Path) -> list[list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"unsupported image header: {path}")

    pos = 8
    width = height = None
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack("!I", data[pos : pos + 4])[0]
        pos += 4
        tag = data[pos : pos + 4]
        pos += 4
        chunk = data[pos : pos + length]
        pos += length + 4

        if tag == b"IHDR":
            width, height, bit_depth, color_type, *_ = struct.unpack("!IIBBBBB", chunk)
            if bit_depth != 8 or color_type != 2:
                raise ValueError("only 8-bit RGB PNG files are supported")
        elif tag == b"IDAT":
            idat.extend(chunk)
        elif tag == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    stride = width * 3
    offset = 0
    pixels: list[list[tuple[int, int, int]]] = []
    for _ in range(height):
        filter_type = raw[offset]
        if filter_type != 0:
            raise ValueError("unexpected PNG filter type")
        offset += 1
        row_bytes = raw[offset : offset + stride]
        offset += stride
        row = [tuple(row_bytes[index : index + 3]) for index in range(0, len(row_bytes), 3)]
        pixels.append(row)
    return pixels


def build_mask(
    pixels: list[list[tuple[int, int, int]]],
    box: tuple[int, int, int, int],
    kind: str,
) -> list[list[bool]]:
    x0, y0, x1, y1 = box
    mask: list[list[bool]] = []
    for y in range(y0, y1):
        row: list[bool] = []
        for x in range(x0, x1):
            r, g, b = pixels[y][x]
            if kind == "team":
                row.append(r > 220 and g > 220 and b > 220)
            else:
                row.append(max(r, g, b) >= 120 and (max(r, g, b) - min(r, g, b)) >= 40)
        mask.append(row)
    return mask


def trim_mask(mask: list[list[bool]]) -> list[list[bool]]:
    ys = [index for index, row in enumerate(mask) if any(row)]
    xs = [index for index in range(len(mask[0])) if any(mask[y][index] for y in range(len(mask)))]
    if not xs or not ys:
        raise ValueError("empty mask")
    x0, x1 = min(xs), max(xs) + 1
    y0, y1 = min(ys), max(ys) + 1
    return [row[x0:x1] for row in mask[y0:y1]]


def split_runs(mask: list[list[bool]]) -> list[tuple[int, int]]:
    filled_columns = [any(mask[y][x] for y in range(len(mask))) for x in range(len(mask[0]))]
    runs: list[tuple[int, int]] = []
    start = None
    for index, filled in enumerate(filled_columns):
        if filled and start is None:
            start = index
        elif not filled and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(filled_columns)))
    return [(start, end) for start, end in runs if end - start >= 8]


def observe_pattern(mask: list[list[bool]]) -> tuple[str, ...]:
    height = len(mask)
    width = len(mask[0])
    rows: list[str] = []
    for gy in range(7):
        y0 = round(gy * height / 7)
        y1 = round((gy + 1) * height / 7)
        bits: list[str] = []
        for gx in range(5):
            x0 = round(gx * width / 5)
            x1 = round((gx + 1) * width / 5)
            total = max(1, (y1 - y0) * (x1 - x0))
            filled = sum(1 for yy in range(y0, y1) for xx in range(x0, x1) if mask[yy][xx])
            bits.append("1" if filled / total >= 0.30 else "0")
        rows.append("".join(bits))
    return tuple(rows)


def nearest_char(pattern: tuple[str, ...], keys: list[str]) -> str:
    best_distance = None
    best_char = None
    for key in keys:
        distance = sum(
            1
            for observed_row, target_row in zip(pattern, FONT[key])
            for observed_bit, target_bit in zip(observed_row, target_row)
            if observed_bit != target_bit
        )
        if best_distance is None or distance < best_distance or (distance == best_distance and key < best_char):
            best_distance = distance
            best_char = key
    return best_char


def decode_text(mask: list[list[bool]], keys: list[str]) -> str:
    cropped = trim_mask(mask)
    chars: list[str] = []
    for start, end in split_runs(cropped):
        char_mask = [row[start:end] for row in cropped]
        chars.append(nearest_char(observe_pattern(char_mask), keys))
    return "".join(chars)


def normalize_team(raw_name: str) -> str:
    def edit_distance(left: str, right: str) -> int:
        previous = list(range(len(right) + 1))
        for i, left_char in enumerate(left, start=1):
            current = [i]
            for j, right_char in enumerate(right, start=1):
                substitution = previous[j - 1] + (0 if left_char == right_char else 1)
                current.append(min(previous[j] + 1, current[j - 1] + 1, substitution))
            previous = current
        return previous[-1]

    best = None
    for candidate in TEAM_CANDIDATES:
        proposal = (edit_distance(raw_name, candidate), candidate)
        if best is None or proposal < best:
            best = proposal
    return best[1]


def extract_match(path: Path) -> tuple[str, int, str, int]:
    pixels = read_png(path)

    left_team = decode_text(build_mask(pixels, (130, 240, 585, 345), "team"), LETTER_KEYS)
    right_team = decode_text(build_mask(pixels, (740, 240, 1185, 345), "team"), LETTER_KEYS)
    left_score = decode_text(build_mask(pixels, (150, 330, 540, 610), "score"), DIGIT_KEYS)
    right_score = decode_text(build_mask(pixels, (760, 330, 1090, 610), "score"), DIGIT_KEYS)

    return normalize_team(left_team), int(left_score), normalize_team(right_team), int(right_score)


teams: dict[str, dict[str, int]] = {}
for image_path in sorted(INPUT_DIR.glob("*.png")):
    left_team, left_score, right_team, right_score = extract_match(image_path)
    for team in (left_team, right_team):
        teams.setdefault(
            team,
            {
                "wins": 0,
                "losses": 0,
                "points_for": 0,
                "points_against": 0,
            },
        )

    teams[left_team]["points_for"] += left_score
    teams[left_team]["points_against"] += right_score
    teams[right_team]["points_for"] += right_score
    teams[right_team]["points_against"] += left_score

    if left_score > right_score:
        teams[left_team]["wins"] += 1
        teams[right_team]["losses"] += 1
    else:
        teams[right_team]["wins"] += 1
        teams[left_team]["losses"] += 1


rows = []
for team, stats in teams.items():
    rows.append(
        {
            "team": team,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "points_for": stats["points_for"],
            "points_against": stats["points_against"],
            "net_point_diff": stats["points_for"] - stats["points_against"],
        }
    )

rows.sort(key=lambda item: (-item["wins"], -item["net_point_diff"], item["team"]))

with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(
        ["rank", "team", "wins", "losses", "points_for", "points_against", "net_point_diff"]
    )
    for index, row in enumerate(rows, start=1):
        writer.writerow(
            [
                index,
                row["team"],
                row["wins"],
                row["losses"],
                row["points_for"],
                row["points_against"],
                row["net_point_diff"],
            ]
        )
PY
