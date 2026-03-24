#!/bin/bash
set -euo pipefail

TASK_WORKSPACE="${TASK_WORKSPACE:-/root/workspace}"

cat > "${TASK_WORKSPACE}/mandelbrot_balance_solution.py" <<'PYTHON_EOF'
#!/usr/bin/env python3
"""
Reference parallel implementation for the Mandelbrot tile renderer task.
"""

from __future__ import annotations

import os
import pickle
import select
import time
from dataclasses import dataclass

from sequential_mandelbrot import (
    DEFAULT_TILE_COLS,
    DEFAULT_TILE_ROWS,
    MandelbrotImage,
    build_tile_jobs,
    pixel_escape_iterations,
    render_mandelbrot_sequential,
    render_tile,
)


@dataclass
class ParallelRenderResult:
    image: MandelbrotImage
    elapsed_time: float
    tile_count: int
    num_workers: int
    strategy: str


@dataclass
class _ForkWorker:
    pid: int
    task_writer: object
    result_reader: object


def _estimate_tile_cost(scene, tile) -> int:
    mid_x = (tile.col_start + tile.col_end - 1) // 2
    mid_y = (tile.row_start + tile.row_end - 1) // 2
    sample_points = [
        (tile.col_start, tile.row_start),
        (tile.col_end - 1, tile.row_start),
        (tile.col_start, tile.row_end - 1),
        (tile.col_end - 1, tile.row_end - 1),
        (mid_x, mid_y),
    ]
    sample_cost = sum(pixel_escape_iterations(scene, x, y) for x, y in sample_points)
    area = (tile.row_end - tile.row_start) * (tile.col_end - tile.col_start)
    return max(sample_cost * max(area, 1), area)


def _spawn_workers(scene, worker_count):
    workers = []
    for _ in range(worker_count):
        parent_to_child_read, parent_to_child_write = os.pipe()
        child_to_parent_read, child_to_parent_write = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(parent_to_child_write)
            os.close(child_to_parent_read)
            _worker_loop(scene, parent_to_child_read, child_to_parent_write)
        os.close(parent_to_child_read)
        os.close(child_to_parent_write)
        workers.append(
            _ForkWorker(
                pid=pid,
                task_writer=os.fdopen(parent_to_child_write, "wb", buffering=0),
                result_reader=os.fdopen(child_to_parent_read, "rb", buffering=0),
            )
        )
    return workers


def _worker_loop(scene, task_read_fd, result_write_fd):
    task_reader = os.fdopen(task_read_fd, "rb", buffering=0)
    result_writer = os.fdopen(result_write_fd, "wb", buffering=0)
    try:
        while True:
            try:
                tile = pickle.load(task_reader)
            except EOFError:
                break
            if tile is None:
                break
            pickle.dump(render_tile(scene, tile), result_writer, protocol=pickle.HIGHEST_PROTOCOL)
            result_writer.flush()
    finally:
        task_reader.close()
        result_writer.close()
        os._exit(0)


def _send_tile(worker, tile):
    pickle.dump(tile, worker.task_writer, protocol=pickle.HIGHEST_PROTOCOL)
    worker.task_writer.flush()


def _close_workers(workers):
    for worker in workers:
        try:
            pickle.dump(None, worker.task_writer, protocol=pickle.HIGHEST_PROTOCOL)
            worker.task_writer.flush()
        except BrokenPipeError:
            pass
        worker.task_writer.close()
        worker.result_reader.close()
        os.waitpid(worker.pid, 0)


def render_mandelbrot_parallel(scene, num_workers=None, tile_rows=DEFAULT_TILE_ROWS, tile_cols=DEFAULT_TILE_COLS):
    jobs = build_tile_jobs(scene, tile_rows=tile_rows, tile_cols=tile_cols)
    worker_count = num_workers or (os.cpu_count() or 1)
    worker_count = max(1, min(int(worker_count), len(jobs) or 1))

    if worker_count == 1 or len(jobs) <= 1:
        sequential = render_mandelbrot_sequential(scene, tile_rows=tile_rows, tile_cols=tile_cols)
        return ParallelRenderResult(
            image=sequential.image,
            elapsed_time=sequential.elapsed_time,
            tile_count=sequential.tile_count,
            num_workers=1,
            strategy="sequential-fallback",
        )

    ordered_jobs = sorted(jobs, key=lambda tile: (-_estimate_tile_cost(scene, tile), tile.index))
    pixels = [[0 for _ in range(scene.width)] for _ in range(scene.height)]
    start_time = time.perf_counter()
    workers = _spawn_workers(scene, worker_count)
    active_readers = {}
    next_job_index = 0
    remaining = len(ordered_jobs)

    try:
        while next_job_index < len(ordered_jobs) and len(active_readers) < len(workers):
            worker = workers[len(active_readers)]
            _send_tile(worker, ordered_jobs[next_job_index])
            active_readers[worker.result_reader.fileno()] = worker
            next_job_index += 1

        while remaining:
            ready_readers, _ignored, _ignored_err = select.select(
                [worker.result_reader for worker in active_readers.values()],
                [],
                [],
            )
            for reader in ready_readers:
                worker = active_readers.pop(reader.fileno())
                _tile_index, rows = pickle.load(reader)
                for y, col_start, pixel_row in rows:
                    pixels[y][col_start : col_start + len(pixel_row)] = pixel_row
                remaining -= 1

                if next_job_index < len(ordered_jobs):
                    _send_tile(worker, ordered_jobs[next_job_index])
                    active_readers[worker.result_reader.fileno()] = worker
                    next_job_index += 1
    finally:
        _close_workers(workers)

    elapsed_time = time.perf_counter() - start_time
    return ParallelRenderResult(
        image=MandelbrotImage(
            scene_name=scene.name,
            width=scene.width,
            height=scene.height,
            max_iter=scene.max_iter,
            pixels=pixels,
        ),
        elapsed_time=elapsed_time,
        tile_count=len(jobs),
        num_workers=worker_count,
        strategy="cost-ranked dynamic tile queue",
    )
PYTHON_EOF

chmod +x "${TASK_WORKSPACE}/mandelbrot_balance_solution.py"
