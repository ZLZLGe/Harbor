#!/usr/bin/env python3
"""
Sequential Mandelbrot tile renderer used as the correctness baseline.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TILE_ROWS = 24
DEFAULT_TILE_COLS = 24
DEFAULT_CATALOG_PATH = Path(__file__).with_name("mandelbrot_scenes.json")


@dataclass(frozen=True)
class RenderScene:
    name: str
    width: int
    height: int
    center_x: float
    center_y: float
    scale: float
    max_iter: int
    escape_radius: float = 2.0


@dataclass(frozen=True)
class TileJob:
    index: int
    row_start: int
    row_end: int
    col_start: int
    col_end: int


@dataclass
class MandelbrotImage:
    scene_name: str
    width: int
    height: int
    max_iter: int
    pixels: list[list[int]]


@dataclass
class RenderResult:
    image: MandelbrotImage
    elapsed_time: float
    tile_count: int


def load_scene_catalog(catalog_path: str | Path = DEFAULT_CATALOG_PATH) -> dict[str, RenderScene]:
    payload = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    return {
        name: RenderScene(
            name=name,
            width=int(config["width"]),
            height=int(config["height"]),
            center_x=float(config["center_x"]),
            center_y=float(config["center_y"]),
            scale=float(config["scale"]),
            max_iter=int(config["max_iter"]),
            escape_radius=float(config.get("escape_radius", 2.0)),
        )
        for name, config in payload.items()
    }


def load_scene(name: str, catalog_path: str | Path = DEFAULT_CATALOG_PATH) -> RenderScene:
    scenes = load_scene_catalog(catalog_path)
    if name not in scenes:
        raise KeyError(f"Unknown scene: {name}")
    return scenes[name]


def pixel_escape_iterations(scene: RenderScene, x: int, y: int) -> int:
    real = scene.center_x + (x - scene.width / 2.0) * (scene.scale / scene.width)
    imag = scene.center_y + (y - scene.height / 2.0) * (scene.scale / scene.width)
    z_real = 0.0
    z_imag = 0.0
    escape_threshold = scene.escape_radius * scene.escape_radius

    for iteration in range(scene.max_iter):
        real_sq = z_real * z_real
        imag_sq = z_imag * z_imag
        if real_sq + imag_sq > escape_threshold:
            return iteration
        z_imag = 2.0 * z_real * z_imag + imag
        z_real = real_sq - imag_sq + real

    return scene.max_iter


def iteration_to_grayscale(iteration: int, max_iter: int) -> int:
    if iteration >= max_iter:
        return 0
    return 255 - int((255 * iteration) / max_iter)


def build_tile_jobs(
    scene: RenderScene,
    tile_rows: int = DEFAULT_TILE_ROWS,
    tile_cols: int = DEFAULT_TILE_COLS,
) -> list[TileJob]:
    tile_rows = max(1, int(tile_rows))
    tile_cols = max(1, int(tile_cols))

    jobs: list[TileJob] = []
    index = 0
    for row_start in range(0, scene.height, tile_rows):
        row_end = min(scene.height, row_start + tile_rows)
        for col_start in range(0, scene.width, tile_cols):
            col_end = min(scene.width, col_start + tile_cols)
            jobs.append(
                TileJob(
                    index=index,
                    row_start=row_start,
                    row_end=row_end,
                    col_start=col_start,
                    col_end=col_end,
                )
            )
            index += 1
    return jobs


def render_tile(scene: RenderScene, tile: TileJob) -> tuple[int, list[tuple[int, int, list[int]]]]:
    rows: list[tuple[int, int, list[int]]] = []
    for y in range(tile.row_start, tile.row_end):
        pixel_row = [
            iteration_to_grayscale(pixel_escape_iterations(scene, x, y), scene.max_iter)
            for x in range(tile.col_start, tile.col_end)
        ]
        rows.append((y, tile.col_start, pixel_row))
    return tile.index, rows


def render_mandelbrot_sequential(
    scene: RenderScene,
    tile_rows: int = DEFAULT_TILE_ROWS,
    tile_cols: int = DEFAULT_TILE_COLS,
) -> RenderResult:
    start_time = time.perf_counter()
    jobs = build_tile_jobs(scene, tile_rows=tile_rows, tile_cols=tile_cols)
    pixels = [[0 for _ in range(scene.width)] for _ in range(scene.height)]

    for tile in jobs:
        _tile_index, rows = render_tile(scene, tile)
        for y, col_start, pixel_row in rows:
            pixels[y][col_start : col_start + len(pixel_row)] = pixel_row

    elapsed_time = time.perf_counter() - start_time
    return RenderResult(
        image=MandelbrotImage(
            scene_name=scene.name,
            width=scene.width,
            height=scene.height,
            max_iter=scene.max_iter,
            pixels=pixels,
        ),
        elapsed_time=elapsed_time,
        tile_count=len(jobs),
    )


def write_pgm(image: MandelbrotImage, output_path: str | Path) -> None:
    output = Path(output_path)
    header = f"P5\n{image.width} {image.height}\n255\n".encode("ascii")
    payload = bytearray()
    for row in image.pixels:
        payload.extend(row)
    output.write_bytes(header + bytes(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Mandelbrot scene sequentially.")
    parser.add_argument("scene_name", help="Scene name from mandelbrot_scenes.json")
    parser.add_argument("--output", default="mandelbrot.pgm", help="Output grayscale PGM path")
    parser.add_argument("--tile-rows", type=int, default=DEFAULT_TILE_ROWS)
    parser.add_argument("--tile-cols", type=int, default=DEFAULT_TILE_COLS)
    args = parser.parse_args()

    scene = load_scene(args.scene_name)
    result = render_mandelbrot_sequential(scene, tile_rows=args.tile_rows, tile_cols=args.tile_cols)
    write_pgm(result.image, args.output)
    print(
        json.dumps(
            {
                "scene": scene.name,
                "elapsed_time": round(result.elapsed_time, 6),
                "tile_count": result.tile_count,
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
