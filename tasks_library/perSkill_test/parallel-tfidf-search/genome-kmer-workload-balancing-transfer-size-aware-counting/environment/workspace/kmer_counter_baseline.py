#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import multiprocessing as mp
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SequenceRecord:
    record_id: str
    source_path: str
    sequence: str

    @property
    def length(self) -> int:
        return len(self.sequence)


def load_manifest(manifest_path: str = "/root/workspace/genome_manifest.json") -> dict:
    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))


def discover_fasta_paths(manifest_path: str = "/root/workspace/genome_manifest.json") -> list[str]:
    manifest = load_manifest(manifest_path)
    return [entry["path"] for entry in manifest["files"]]


def parse_fasta(path: str) -> list[SequenceRecord]:
    records = []
    header = None
    chunks = []
    source_path = str(path)

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append(SequenceRecord(header, source_path, "".join(chunks)))
                header = line[1:]
                chunks = []
            else:
                chunks.append(line.upper())

    if header is not None:
        records.append(SequenceRecord(header, source_path, "".join(chunks)))
    return records


def load_fasta_records(fasta_paths: list[str] | None = None) -> list[SequenceRecord]:
    paths = fasta_paths or discover_fasta_paths()
    records = []
    for path in paths:
        records.extend(parse_fasta(path))
    return records


def _count_batch(batch: list[tuple[str, int, str]], k: int) -> tuple[dict[str, int], dict]:
    counter = Counter()
    base_load = 0
    kmers_emitted = 0

    for _record_id, length, sequence in batch:
        base_load += length
        windows = max(0, length - k + 1)
        kmers_emitted += windows
        for start in range(windows):
            counter[sequence[start : start + k]] += 1

    return dict(counter), {
        "sequence_count": len(batch),
        "base_load": base_load,
        "kmers_emitted": kmers_emitted,
    }


def _worker_entry(batch: list[tuple[str, int, str]], k: int, connection) -> None:
    try:
        connection.send(_count_batch(batch, k))
    finally:
        connection.close()


def merge_count_dicts(partials: list[dict[str, int]]) -> dict[str, int]:
    merged = Counter()
    for partial in partials:
        merged.update(partial)
    return dict(sorted(merged.items()))


def execute_parallel_batches(
    work_items: list[list[tuple[str, int, str]]],
    k: int,
    num_workers: int,
) -> tuple[list[dict[str, int]], list[dict]]:
    ctx = mp.get_context("fork")
    processes = []
    receivers = []

    for batch in work_items[:num_workers]:
        receiver, sender = ctx.Pipe(duplex=False)
        process = ctx.Process(target=_worker_entry, args=(batch, k, sender))
        process.start()
        sender.close()
        processes.append(process)
        receivers.append(receiver)

    partial_counts = []
    stats_list = []

    for receiver in receivers:
        counts, stats = receiver.recv()
        receiver.close()
        partial_counts.append(counts)
        stats_list.append(stats)

    for process in processes:
        process.join()
        if process.exitcode != 0:
            raise RuntimeError(f"worker exited with code {process.exitcode}")

    return partial_counts, stats_list


def write_outputs(counts: dict[str, int], report: dict, output_path: str, report_path: str, k: int) -> None:
    output_file = Path(output_path)
    report_file = Path(report_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    output_payload = {
        "k": k,
        "total_sequences": report["total_sequences"],
        "counts": dict(sorted(counts.items())),
    }

    output_file.write_text(json.dumps(output_payload, indent=2, sort_keys=True), encoding="utf-8")
    report_file.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def count_kmers_sequential(
    fasta_paths: list[str] | None = None,
    k: int = 6,
    output_path: str = "/root/workspace/sequential_kmer_counts.json",
    report_path: str = "/root/workspace/sequential_kmer_report.json",
):
    records = load_fasta_records(fasta_paths)
    batch = [(record.record_id, record.length, record.sequence) for record in records]

    start_time = time.perf_counter()
    counts, stats = _count_batch(batch, k)
    elapsed_seconds = time.perf_counter() - start_time

    report = {
        "k": k,
        "num_workers": 1,
        "total_sequences": len(records),
        "total_bases": sum(record.length for record in records),
        "distinct_kmers": len(counts),
        "elapsed_seconds": elapsed_seconds,
        "worker_stats": [
            {
                "worker_id": 0,
                "sequence_count": stats["sequence_count"],
                "base_load": stats["base_load"],
                "kmers_emitted": stats["kmers_emitted"],
            }
        ],
    }
    write_outputs(counts, report, output_path, report_path, k)
    return report


def even_split_records(records: list[SequenceRecord], num_workers: int) -> list[list[SequenceRecord]]:
    if num_workers <= 0:
        raise ValueError("num_workers must be positive")

    chunk_size = math.ceil(len(records) / num_workers)
    chunks = []
    for worker_id in range(num_workers):
        start = worker_id * chunk_size
        end = start + chunk_size
        chunks.append(records[start:end])
    return chunks


def run_naive_equal_split(
    fasta_paths: list[str] | None = None,
    k: int = 6,
    output_path: str = "/root/workspace/naive_kmer_counts.json",
    report_path: str = "/root/workspace/naive_kmer_report.json",
    num_workers: int = 2,
):
    records = load_fasta_records(fasta_paths)
    assignments = even_split_records(records, num_workers)
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
