#!/bin/bash

set -euo pipefail

cat > /root/workspace/log_summarizer_parallel.py <<'PYTHON_EOF'
#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from log_summarizer_sequential import (
    LogSummaryResult,
    build_report,
    load_manifest,
    summarize_single_gzip_file,
)


def _process_entry(task: tuple[str, dict]) -> dict:
    log_dir, entry = task
    return summarize_single_gzip_file(log_dir, entry)


def summarize_gzip_logs_parallel(
    log_dir: str | Path = "/root/workspace/gzip_logs",
    manifest_path: str | Path = "/root/workspace/log_manifest.json",
    num_workers: int | None = None,
) -> LogSummaryResult:
    manifest = load_manifest(manifest_path)
    entries = list(manifest["files"])
    if not entries:
        return LogSummaryResult(file_digests=[], report=build_report(manifest, []), elapsed_time=0.0, num_workers=1)

    requested_workers = num_workers or (os.cpu_count() or 1)
    actual_workers = max(1, min(requested_workers, len(entries)))

    start_time = time.perf_counter()
    tasks = [(str(log_dir), entry) for entry in entries]

    if actual_workers == 1:
        partial_results = [_process_entry(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=actual_workers) as executor:
            partial_results = list(executor.map(_process_entry, tasks))

    elapsed_time = time.perf_counter() - start_time

    return LogSummaryResult(
        file_digests=[partial["digest"] for partial in partial_results],
        report=build_report(manifest, partial_results),
        elapsed_time=elapsed_time,
        num_workers=actual_workers,
    )


def write_summary_report_parallel(
    log_dir: str | Path = "/root/workspace/gzip_logs",
    manifest_path: str | Path = "/root/workspace/log_manifest.json",
    output_path: str | Path = "/root/workspace/log_summary_report.json",
    num_workers: int | None = None,
) -> dict:
    result = summarize_gzip_logs_parallel(
        log_dir=log_dir,
        manifest_path=manifest_path,
        num_workers=num_workers,
    )
    Path(output_path).write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    return result.report


__all__ = [
    "summarize_gzip_logs_parallel",
    "write_summary_report_parallel",
]
PYTHON_EOF
