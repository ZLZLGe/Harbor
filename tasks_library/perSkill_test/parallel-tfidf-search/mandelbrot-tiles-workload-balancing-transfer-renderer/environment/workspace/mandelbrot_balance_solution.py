#!/usr/bin/env python3
"""
Starter file for the Mandelbrot tile renderer transfer task.
"""

from __future__ import annotations

from dataclasses import dataclass

from sequential_mandelbrot import DEFAULT_TILE_COLS, DEFAULT_TILE_ROWS, MandelbrotImage


@dataclass
class ParallelRenderResult:
    image: MandelbrotImage
    elapsed_time: float
    tile_count: int
    num_workers: int
    strategy: str


def render_mandelbrot_parallel(scene, num_workers=None, tile_rows=DEFAULT_TILE_ROWS, tile_cols=DEFAULT_TILE_COLS):
    raise NotImplementedError("Implement render_mandelbrot_parallel in this file.")
