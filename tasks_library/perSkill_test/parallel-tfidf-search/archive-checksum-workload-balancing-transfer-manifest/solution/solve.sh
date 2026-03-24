#!/bin/bash
set -euo pipefail

cat > /root/workspace/checksum_balance_solution.py <<'PYTHON_EOF'
#!/usr/bin/env python3
"""
Reference solution for the archive checksum manifest task.
"""

from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from sequential_manifest import (
    ChecksumManifest,
    DEFAULT_BLOCK_SIZE,
    FileJob,
    ManifestBuildResult,
    ManifestEntry,
    discover_file_jobs,
    hash_file,
)


@dataclass
class ParallelManifestResult:
    manifest: ChecksumManifest
    elapsed_time: float
    num_files: int
    total_size_bytes: int
    num_workers: int
    strategy: str


def _hash_job_batch(args: tuple[list[FileJob], int]) -> list[tuple[int, ManifestEntry]]:
    jobs, block_size = args
    results: list[tuple[int, ManifestEntry]] = []
    for job in jobs:
        sha256_digest, block_digest = hash_file(job.absolute_path, block_size=block_size)
        results.append(
            (
                job.index,
                ManifestEntry(
                    relative_path=job.relative_path,
                    size_bytes=job.size_bytes,
                    sha256=sha256_digest,
                    block_digest=block_digest,
                ),
            )
        )
    return results


def _build_weighted_batches(
    jobs: list[FileJob],
    num_workers: int,
    chunk_size: int,
) -> list[list[FileJob]]:
    if not jobs:
        return []

    chunk_size = max(1, chunk_size)
    target_batches = max(num_workers * 4, math.ceil(len(jobs) / chunk_size))
    batch_count = min(len(jobs), target_batches)

    batches: list[list[FileJob]] = [[] for _ in range(batch_count)]
    batch_bytes = [0] * batch_count

    for job in sorted(jobs, key=lambda item: (-item.size_bytes, item.relative_path)):
        candidate_indexes = [index for index, batch in enumerate(batches) if len(batch) < chunk_size]
        if candidate_indexes:
            target_index = min(candidate_indexes, key=lambda index: (batch_bytes[index], len(batches[index]), index))
        else:
            target_index = min(range(len(batches)), key=lambda index: (batch_bytes[index], len(batches[index]), index))
        batches[target_index].append(job)
        batch_bytes[target_index] += max(job.size_bytes, 1)

    ordered = sorted(
        zip(batches, batch_bytes),
        key=lambda item: (-item[1], item[0][0].relative_path if item[0] else ""),
    )
    return [batch for batch, _ in ordered if batch]


def build_checksum_manifest_parallel(root_dir, num_workers=None, chunk_size=8):
    jobs = discover_file_jobs(root_dir)
    if num_workers is None:
        num_workers = 4
    else:
        num_workers = max(1, int(num_workers))

    start_time = time.perf_counter()
    batches = _build_weighted_batches(jobs, num_workers=num_workers, chunk_size=chunk_size)
    indexed_entries: dict[int, ManifestEntry] = {}

    if batches:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(_hash_job_batch, (batch, DEFAULT_BLOCK_SIZE))
                for batch in batches
            ]
            for future in as_completed(futures):
                batch_result = future.result()
                for index, entry in batch_result:
                    indexed_entries[index] = entry

    entries = [indexed_entries[index] for index in range(len(jobs))]
    total_size_bytes = sum(entry.size_bytes for entry in entries)
    manifest = ChecksumManifest(
        root_dir=str(root_dir),
        algorithm="sha256",
        entries=entries,
        total_files=len(entries),
        total_size_bytes=total_size_bytes,
    )

    elapsed_time = time.perf_counter() - start_time
    return ParallelManifestResult(
        manifest=manifest,
        elapsed_time=elapsed_time,
        num_files=len(entries),
        total_size_bytes=total_size_bytes,
        num_workers=num_workers,
        strategy="size-prioritized dynamic batches",
    )
PYTHON_EOF

chmod +x /root/workspace/checksum_balance_solution.py
