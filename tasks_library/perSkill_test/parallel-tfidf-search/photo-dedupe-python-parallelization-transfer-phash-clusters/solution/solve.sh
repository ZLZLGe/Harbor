#!/bin/bash
set -euo pipefail

WORKSPACE_DIR="${TASK_WORKSPACE:-/root/workspace}"

cat > "${WORKSPACE_DIR}/parallel_photo_dedupe.py" <<'PYTHON_EOF'
#!/usr/bin/env python3
"""
Parallel perceptual-hash photo dedupe implementation.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from photo_fixture import discover_photo_paths
from sequential_photo_dedupe import (
    BuildResult,
    PhotoHashIndex,
    PhotoHashRecord,
    build_duplicate_report,
    cluster_duplicate_records,
    compute_perceptual_hash,
)


def _chunked(items: list[str], chunk_size: int) -> list[list[str]]:
    size = max(1, chunk_size)
    return [items[index : index + size] for index in range(0, len(items), size)]


def _hash_batch(args: tuple[list[str], int]) -> list[PhotoHashRecord]:
    batch, hash_size = args
    return [compute_perceptual_hash(photo_path, hash_size=hash_size) for photo_path in batch]


@dataclass
class ParallelHashBuildResult:
    index: PhotoHashIndex
    elapsed_time: float
    num_photos: int
    hash_size: int
    num_workers: int
    chunk_size: int


def build_photo_index_parallel(
    album_dir: str,
    hash_size: int = 8,
    num_workers: int | None = None,
    chunk_size: int = 12,
) -> ParallelHashBuildResult:
    photo_paths = discover_photo_paths(album_dir)
    if not photo_paths:
        empty_index = PhotoHashIndex(hash_size=hash_size)
        return ParallelHashBuildResult(
            index=empty_index,
            elapsed_time=0.0,
            num_photos=0,
            hash_size=hash_size,
            num_workers=0,
            chunk_size=max(1, chunk_size),
        )

    start = time.perf_counter()
    batches = _chunked(photo_paths, chunk_size)
    workers = num_workers or (os.cpu_count() or 1)
    workers = max(1, min(workers, len(batches)))

    with ProcessPoolExecutor(max_workers=workers) as executor:
        partial_batches = list(executor.map(_hash_batch, [(batch, hash_size) for batch in batches]))

    records: list[PhotoHashRecord] = []
    for partial_batch in partial_batches:
        records.extend(partial_batch)

    index = PhotoHashIndex(
        hash_size=hash_size,
        photo_records=records,
        photo_lookup={record.photo_id: record for record in records},
    )
    return ParallelHashBuildResult(
        index=index,
        elapsed_time=time.perf_counter() - start,
        num_photos=len(records),
        hash_size=hash_size,
        num_workers=workers,
        chunk_size=max(1, chunk_size),
    )


def run_photo_dedupe_parallel(
    album_dir: str,
    hash_size: int = 8,
    max_hamming_distance: int = 18,
    num_workers: int | None = None,
    chunk_size: int = 12,
) -> dict:
    build_result = build_photo_index_parallel(
        album_dir,
        hash_size=hash_size,
        num_workers=num_workers,
        chunk_size=chunk_size,
    )
    clusters = cluster_duplicate_records(
        build_result.index,
        max_hamming_distance=max_hamming_distance,
    )
    return build_duplicate_report(
        build_result.index,
        clusters,
        elapsed_time=build_result.elapsed_time,
        max_hamming_distance=max_hamming_distance,
        num_workers=build_result.num_workers,
        chunk_size=build_result.chunk_size,
    )


def main() -> BuildResult:
    import argparse

    parser = argparse.ArgumentParser(description="Parallel perceptual-hash photo dedupe")
    parser.add_argument("album_dir", type=str)
    parser.add_argument("--hash-size", type=int, default=8)
    parser.add_argument("--distance", type=int, default=18)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=12)
    args = parser.parse_args()

    report = run_photo_dedupe_parallel(
        args.album_dir,
        hash_size=args.hash_size,
        max_hamming_distance=args.distance,
        num_workers=args.workers,
        chunk_size=args.chunk_size,
    )
    print(report)
    return build_photo_index_parallel(
        args.album_dir,
        hash_size=args.hash_size,
        num_workers=args.workers,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
PYTHON_EOF

chmod +x "${WORKSPACE_DIR}/parallel_photo_dedupe.py"
