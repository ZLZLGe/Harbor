#!/bin/bash

set -euo pipefail

python3 - <<'PY'
import os
from collections import deque
from pathlib import Path

from PIL import Image


workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_dir = workspace_root / "greenhouse_frames"
output_path = workspace_root / "growth_timeline.tsv"


def connected_components(mask, min_pixels):
    height = len(mask)
    width = len(mask[0]) if height else 0
    visited = [[False] * width for _ in range(height)]
    count = 0

    for y in range(height):
        for x in range(width):
            if not mask[y][x] or visited[y][x]:
                continue

            queue = deque([(x, y)])
            visited[y][x] = True
            pixels = 0

            while queue:
                cx, cy = queue.popleft()
                pixels += 1
                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        if mask[ny][nx] and not visited[ny][nx]:
                            visited[ny][nx] = True
                            queue.append((nx, ny))

            if pixels >= min_pixels:
                count += 1

    return count


def build_masks(image):
    rgb = image.convert("RGB")
    width, height = rgb.size
    flower_mask = [[False] * width for _ in range(height)]
    fruit_mask = [[False] * width for _ in range(height)]
    lesion_mask = [[False] * width for _ in range(height)]

    for y in range(height):
        for x in range(width):
            r, g, b = rgb.getpixel((x, y))
            flower_mask[y][x] = r >= 240 and 110 <= g <= 180 and b <= 90
            fruit_mask[y][x] = r >= 180 and g <= 90 and b <= 90
            lesion_mask[y][x] = 110 <= r <= 135 and g <= 40 and 30 <= b <= 55

    return flower_mask, fruit_mask, lesion_mask


def analyze_image(path):
    with Image.open(path) as image:
        flower_mask, fruit_mask, lesion_mask = build_masks(image)

    flowering_plants = connected_components(flower_mask, min_pixels=80)
    ripe_fruits = connected_components(fruit_mask, min_pixels=250)
    diseased_leaves = connected_components(lesion_mask, min_pixels=60)

    return {
        "date": path.stem,
        "flowering_plants": flowering_plants,
        "ripe_fruits": ripe_fruits,
        "diseased_leaves": diseased_leaves,
    }


def earliest_peak(rows, key):
    best_row = rows[0]
    for row in rows[1:]:
        if row[key] > best_row[key]:
            best_row = row
    return best_row["date"], best_row[key]


image_paths = sorted(
    path for path in input_dir.iterdir()
    if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
)
rows = [analyze_image(path) for path in image_paths]

peak_metrics = []
for metric in ("flowering_plants", "ripe_fruits", "diseased_leaves"):
    peak_date, peak_value = earliest_peak(rows, metric)
    peak_metrics.append((metric, peak_date, peak_value))

lines = [
    "[daily_counts]",
    "date\tflowering_plants\tripe_fruits\tdiseased_leaves",
]

for row in rows:
    lines.append(
        f"{row['date']}\t{row['flowering_plants']}\t{row['ripe_fruits']}\t{row['diseased_leaves']}"
    )

lines.extend(
    [
        "",
        "[peak_dates]",
        "metric\tpeak_date\tpeak_value",
    ]
)

for metric, peak_date, peak_value in peak_metrics:
    lines.append(f"{metric}\t{peak_date}\t{peak_value}")

output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
