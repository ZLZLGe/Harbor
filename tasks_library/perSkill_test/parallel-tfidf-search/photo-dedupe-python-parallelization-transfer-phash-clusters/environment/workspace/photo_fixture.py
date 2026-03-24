#!/usr/bin/env python3
"""
Deterministic helpers for perceptual-hash photo dedupe tasks.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class PhotoSpec:
    photo_id: str
    scene_seed: int
    capture_group: str
    width: int = 96
    height: int = 96
    shift_x: int = 0
    shift_y: int = 0
    brightness_offset: int = 0
    contrast_percent: int = 100
    noise_level: int = 0
    vignette_strength: int = 0
    accent_seed: int = 0


def clamp_byte(value: float) -> int:
    return max(0, min(255, int(round(value))))


def load_album_blueprint(path: str | Path) -> list[PhotoSpec]:
    raw_items = json.loads(Path(path).read_text())
    return [PhotoSpec(**item) for item in raw_items]


def save_album_blueprint(path: str | Path, specs: list[PhotoSpec]) -> None:
    payload = [asdict(spec) for spec in specs]
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def generate_album_blueprint(
    num_groups: int,
    variants_per_group: int,
    seed: int = 20260322,
    width: int = 148,
    height: int = 148,
) -> list[PhotoSpec]:
    rng = random.Random(seed)
    specs: list[PhotoSpec] = []

    for group_index in range(num_groups):
        scene_seed = 100 + group_index * 17
        capture_group = f"burst-{group_index:03d}"
        for variant_index in range(variants_per_group):
            specs.append(
                PhotoSpec(
                    photo_id=f"{capture_group}_{variant_index:02d}",
                    scene_seed=scene_seed,
                    capture_group=capture_group,
                    width=width,
                    height=height,
                    shift_x=rng.randint(-2, 2),
                    shift_y=rng.randint(-2, 2),
                    brightness_offset=rng.randint(-10, 10),
                    contrast_percent=100 + rng.randint(-6, 6),
                    noise_level=rng.randint(2, 8),
                    vignette_strength=rng.randint(0, 6),
                    accent_seed=variant_index + 1,
                )
            )

    for unique_index in range(max(2, num_groups // 4)):
        specs.append(
            PhotoSpec(
                photo_id=f"unique_{unique_index:02d}",
                scene_seed=1000 + unique_index * 19,
                capture_group=f"unique-{unique_index:02d}",
                width=width,
                height=height,
                shift_x=0,
                shift_y=0,
                brightness_offset=rng.randint(-4, 4),
                contrast_percent=100,
                noise_level=2,
                vignette_strength=1,
                accent_seed=700 + unique_index,
            )
        )

    return specs


def _shifted_value(matrix: list[list[int]], x: int, y: int, shift_x: int, shift_y: int) -> int:
    src_y = min(max(y - shift_y, 0), len(matrix) - 1)
    src_x = min(max(x - shift_x, 0), len(matrix[0]) - 1)
    return matrix[src_y][src_x]


def _build_base_scene(scene_seed: int, width: int, height: int) -> list[list[int]]:
    rng = random.Random(scene_seed)
    band = (scene_seed % 5) + 3
    peaks = [
        (
            rng.randint(0, width - 1),
            rng.randint(0, height - 1),
            rng.randint(max(8, min(width, height) // 6), max(12, min(width, height) // 3)),
            rng.randint(40, 110),
        )
        for _ in range(5)
    ]

    pixels: list[list[int]] = []
    for y in range(height):
        row: list[int] = []
        for x in range(width):
            value = (
                x * (scene_seed % 7 + 3)
                + y * (scene_seed % 11 + 5)
                + ((x * y) % 31) * 2
                + ((x ^ y) % 17) * band
                + scene_seed * 13
            ) % 256

            if (x // max(1, width // 6)) % 2 == 0:
                value = clamp_byte(value + 18)
            if (y // max(1, height // 7)) % 3 == 1:
                value = clamp_byte(value - 12)

            for peak_x, peak_y, radius, amplitude in peaks:
                distance = abs(x - peak_x) + abs(y - peak_y)
                if distance < radius:
                    value = clamp_byte(value + amplitude - distance)

            row.append(value)
        pixels.append(row)

    return pixels


def render_photo_pixels(spec: PhotoSpec) -> list[list[int]]:
    base = _build_base_scene(spec.scene_seed, spec.width, spec.height)
    rng = random.Random(spec.scene_seed * 1000 + spec.accent_seed * 37)

    pixels: list[list[int]] = []
    for y in range(spec.height):
        row: list[int] = []
        for x in range(spec.width):
            value = _shifted_value(base, x, y, spec.shift_x, spec.shift_y)
            value = ((value - 128) * spec.contrast_percent) / 100.0 + 128 + spec.brightness_offset

            if spec.vignette_strength:
                edge_distance = min(x, y, spec.width - 1 - x, spec.height - 1 - y)
                vignette = max(0, spec.vignette_strength * 3 - edge_distance // 5)
                value -= vignette

            if spec.noise_level:
                value += rng.randint(-spec.noise_level, spec.noise_level)

            row.append(clamp_byte(value))
        pixels.append(row)

    return pixels


def write_pgm(path: str | Path, pixels: list[list[int]]) -> None:
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    lines = ["P2", f"{width} {height}", "255"]
    for row in pixels:
        lines.append(" ".join(str(value) for value in row))
    Path(path).write_text("\n".join(lines) + "\n")


def read_pgm(path: str | Path) -> list[list[int]]:
    tokens: list[str] = []
    for raw_line in Path(path).read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tokens.extend(line.split())

    if len(tokens) < 4 or tokens[0] != "P2":
        raise ValueError(f"Unsupported PGM file: {path}")

    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    if max_value <= 0:
        raise ValueError(f"Invalid max value in {path}")

    values = [int(token) for token in tokens[4:]]
    if len(values) != width * height:
        raise ValueError(f"Unexpected pixel count in {path}")

    rows: list[list[int]] = []
    index = 0
    for _ in range(height):
        rows.append(values[index : index + width])
        index += width
    return rows


def materialize_album(specs: list[PhotoSpec], output_dir: str | Path) -> list[str]:
    album_dir = Path(output_dir)
    album_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[str] = []
    for spec in specs:
        photo_path = album_dir / f"{spec.photo_id}.pgm"
        write_pgm(photo_path, render_photo_pixels(spec))
        written_paths.append(str(photo_path))

    return written_paths


def materialize_album_from_blueprint(blueprint_path: str | Path, output_dir: str | Path) -> list[str]:
    return materialize_album(load_album_blueprint(blueprint_path), output_dir)


def discover_photo_paths(album_dir: str | Path) -> list[str]:
    return [str(path) for path in sorted(Path(album_dir).glob("*.pgm"))]


def resize_to_square(pixels: list[list[int]], target_size: int) -> list[list[float]]:
    source_height = len(pixels)
    source_width = len(pixels[0]) if pixels else 0
    if source_height == 0 or source_width == 0:
        return [[0.0 for _ in range(target_size)] for _ in range(target_size)]

    resized: list[list[float]] = []
    for row_index in range(target_size):
        source_y = min(source_height - 1, int(row_index * source_height / target_size))
        row: list[float] = []
        for col_index in range(target_size):
            source_x = min(source_width - 1, int(col_index * source_width / target_size))
            row.append(float(pixels[source_y][source_x]))
        resized.append(row)
    return resized


def basename_id(photo_path: str | Path) -> str:
    return Path(photo_path).stem


def hamming_distance(hash_a: int, hash_b: int) -> int:
    return (hash_a ^ hash_b).bit_count()


def expected_groups_from_specs(specs: list[PhotoSpec]) -> list[list[str]]:
    grouped: dict[str, list[str]] = {}
    for spec in specs:
        grouped.setdefault(spec.capture_group, []).append(spec.photo_id)

    return sorted(
        [sorted(members) for members in grouped.values() if len(members) > 1],
        key=lambda members: members[0],
    )
