#!/bin/bash

set -euo pipefail

python - <<'PY'
from pathlib import Path

content = r'''#!/usr/bin/env python3
from __future__ import annotations

import time

from kmer_counter_baseline import (
    SequenceRecord,
    discover_fasta_paths,
    execute_parallel_batches,
    load_fasta_records,
    merge_count_dicts,
    write_outputs,
)


def _weighted_assign(records: list[SequenceRecord], num_workers: int) -> list[list[SequenceRecord]]:
    assignments = [[] for _ in range(num_workers)]
    loads = [0] * num_workers

    for record in sorted(records, key=lambda item: item.length, reverse=True):
        worker_id = min(range(num_workers), key=lambda index: loads[index])
        assignments[worker_id].append(record)
        loads[worker_id] += record.length

    return assignments


def count_kmers_balanced(
    fasta_paths=None,
    k=6,
    output_path="/root/workspace/kmer_counts.json",
    report_path="/root/workspace/kmer_report.json",
    num_workers=2,
):
    if num_workers <= 0:
        raise ValueError("num_workers must be positive")

    paths = fasta_paths or discover_fasta_paths()
    records = load_fasta_records(paths)
    assignments = _weighted_assign(records, num_workers)
    work_items = [
        [(record.record_id, record.length, record.sequence) for record in batch]
        for batch in assignments
    ]

    start_time = time.perf_counter()
    partial_counts, stats_list = execute_parallel_batches(work_items, k, num_workers)
    worker_stats = []
    for worker_id, stats in enumerate(stats_list):
        worker_stats.append(
            {
                "worker_id": worker_id,
                "sequence_count": stats["sequence_count"],
                "base_load": stats["base_load"],
                "kmers_emitted": stats["kmers_emitted"],
            }
        )

    counts = merge_count_dicts(partial_counts)
    elapsed_seconds = time.perf_counter() - start_time

    report = {
        "k": k,
        "num_workers": num_workers,
        "total_sequences": len(records),
        "total_bases": sum(record.length for record in records),
        "distinct_kmers": len(counts),
        "elapsed_seconds": elapsed_seconds,
        "worker_stats": worker_stats,
    }
    write_outputs(counts, report, output_path, report_path, k)
    return report
'''

Path("/root/workspace/kmer_counter_balanced.py").write_text(content, encoding="utf-8")
PY
