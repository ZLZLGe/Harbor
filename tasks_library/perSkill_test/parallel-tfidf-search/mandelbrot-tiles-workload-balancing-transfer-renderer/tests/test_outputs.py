#!/usr/bin/env python3
"""
Tests for the Mandelbrot tile renderer transfer task.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

WORKSPACE_DIR = Path(os.environ.get("TASK_WORKSPACE", "/root/workspace"))
sys.path.insert(0, str(WORKSPACE_DIR))

from sequential_mandelbrot import load_scene, render_mandelbrot_sequential


def image_signature(image) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    for row in image.pixels:
        digest.update(bytes(row))
        total += sum(row)
    return digest.hexdigest(), total


class TestParallelInterface:
    def test_parallel_solution_exists(self):
        try:
            from mandelbrot_balance_solution import render_mandelbrot_parallel  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"Could not import mandelbrot_balance_solution: {exc}")


class TestCorrectness:
    def test_small_scene_matches_baseline(self):
        from mandelbrot_balance_solution import render_mandelbrot_parallel

        scene = replace(load_scene("boundary_study"), width=96, height=72, scale=0.024, max_iter=220)
        sequential = render_mandelbrot_sequential(scene, tile_rows=12, tile_cols=12)
        parallel = render_mandelbrot_parallel(scene, num_workers=4, tile_rows=12, tile_cols=12)

        assert parallel.tile_count == sequential.tile_count
        assert parallel.image == sequential.image

    def test_parallel_output_is_deterministic(self):
        from mandelbrot_balance_solution import render_mandelbrot_parallel

        scene = load_scene("filament_probe")
        expected = render_mandelbrot_sequential(scene, tile_rows=16, tile_cols=16)
        parallel_a = render_mandelbrot_parallel(scene, num_workers=4, tile_rows=16, tile_cols=16)
        parallel_b = render_mandelbrot_parallel(scene, num_workers=3, tile_rows=20, tile_cols=14)

        assert image_signature(parallel_a.image) == image_signature(expected.image)
        assert image_signature(parallel_b.image) == image_signature(expected.image)


class TestPerformance:
    def test_parallel_is_faster_on_tail_heavy_scene(self):
        from mandelbrot_balance_solution import render_mandelbrot_parallel

        scene = load_scene("tail_heavy")

        render_mandelbrot_parallel(scene, num_workers=4, tile_rows=24, tile_cols=24)

        seq_times = []
        para_times = []
        for _ in range(2):
            start = time.perf_counter()
            sequential = render_mandelbrot_sequential(scene, tile_rows=24, tile_cols=24)
            seq_times.append(time.perf_counter() - start)

            start = time.perf_counter()
            parallel = render_mandelbrot_parallel(scene, num_workers=4, tile_rows=24, tile_cols=24)
            para_times.append(time.perf_counter() - start)

        speedup = min(seq_times) / min(para_times)

        print("\nMandelbrot Render Performance:")
        print(f"  Sequential best: {min(seq_times):.3f}s")
        print(f"  Parallel best:   {min(para_times):.3f}s")
        print(f"  Speedup:         {speedup:.2f}x")

        assert image_signature(parallel.image) == image_signature(sequential.image)
        assert speedup >= 1.20, f"Insufficient speedup: {speedup:.2f}x (required: 1.20x)"
