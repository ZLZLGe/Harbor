#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from statistics import median

import pytest


WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE", "/root/workspace"))
LOG_DIR = WORKSPACE_ROOT / "gzip_logs"
MANIFEST_PATH = WORKSPACE_ROOT / "log_manifest.json"
sys.path.insert(0, str(WORKSPACE_ROOT))

from log_summarizer_sequential import (
    file_digests_as_dicts,
    load_manifest,
    summarize_gzip_logs_sequential,
    write_summary_report_sequential,
)


MANIFEST = load_manifest(MANIFEST_PATH)
SERVICE_ORDER = list(MANIFEST["services"])
MIN_EXPECTED_MEDIAN_RUNTIME = 0.4


def load_parallel_module():
    module_path = WORKSPACE_ROOT / "log_summarizer_parallel.py"
    if not module_path.exists():
        pytest.fail(f"Expected output file was not created: {module_path}")

    spec = importlib.util.spec_from_file_location("log_summarizer_parallel", module_path)
    if spec is None or spec.loader is None:
        pytest.fail(f"Unable to load module from {module_path}")

    sys.modules.pop("log_summarizer_parallel", None)
    module = importlib.util.module_from_spec(spec)
    sys.modules["log_summarizer_parallel"] = module
    spec.loader.exec_module(module)
    return module


def benchmark_report_writing(module, repeats=3):
    sequential_times = []
    parallel_times = []

    write_summary_report_sequential(
        log_dir=LOG_DIR,
        manifest_path=MANIFEST_PATH,
        output_path=WORKSPACE_ROOT / "_warmup_seq_report.json",
    )
    module.write_summary_report_parallel(
        log_dir=LOG_DIR,
        manifest_path=MANIFEST_PATH,
        output_path=WORKSPACE_ROOT / "_warmup_parallel_report.json",
        num_workers=2,
    )

    for run_index in range(repeats):
        start = time.perf_counter()
        write_summary_report_sequential(
            log_dir=LOG_DIR,
            manifest_path=MANIFEST_PATH,
            output_path=WORKSPACE_ROOT / f"_seq_report_{run_index}.json",
        )
        sequential_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        module.write_summary_report_parallel(
            log_dir=LOG_DIR,
            manifest_path=MANIFEST_PATH,
            output_path=WORKSPACE_ROOT / f"_parallel_report_{run_index}.json",
            num_workers=2,
        )
        parallel_times.append(time.perf_counter() - start)

    return median(sequential_times), median(parallel_times)


class TestInterface:
    def test_output_file_and_functions_exist(self):
        module = load_parallel_module()
        assert hasattr(module, "summarize_gzip_logs_parallel")
        assert hasattr(module, "write_summary_report_parallel")


class TestCorrectness:
    def test_parallel_summary_matches_baseline(self):
        module = load_parallel_module()
        expected = summarize_gzip_logs_sequential(log_dir=LOG_DIR, manifest_path=MANIFEST_PATH)

        start = time.perf_counter()
        actual = module.summarize_gzip_logs_parallel(
            log_dir=LOG_DIR,
            manifest_path=MANIFEST_PATH,
            num_workers=2,
        )
        wall_time = time.perf_counter() - start

        assert actual.num_workers == 2
        assert file_digests_as_dicts(actual.file_digests) == file_digests_as_dicts(expected.file_digests)
        assert actual.report == expected.report
        assert [digest.filename for digest in actual.file_digests] == [
            entry["filename"] for entry in MANIFEST["files"]
        ]
        assert [row["service"] for row in actual.report["service_summary"]] == SERVICE_ORDER
        assert abs(actual.elapsed_time - wall_time) < 0.25

    def test_report_writer_matches_baseline_json(self, tmp_path):
        module = load_parallel_module()
        expected_path = tmp_path / "expected_report.json"
        actual_path = tmp_path / "actual_report.json"

        expected_report = write_summary_report_sequential(
            log_dir=LOG_DIR,
            manifest_path=MANIFEST_PATH,
            output_path=expected_path,
        )
        actual_report = module.write_summary_report_parallel(
            log_dir=LOG_DIR,
            manifest_path=MANIFEST_PATH,
            output_path=actual_path,
            num_workers=2,
        )

        assert actual_report == expected_report
        assert json.loads(actual_path.read_text(encoding="utf-8")) == json.loads(
            expected_path.read_text(encoding="utf-8")
        )


class TestPerformance:
    def test_parallel_speedup(self):
        module = load_parallel_module()
        sequential_time, parallel_time = benchmark_report_writing(module)
        speedup = sequential_time / parallel_time

        print(f"\nSequential median: {sequential_time:.4f}s")
        print(f"Parallel median:   {parallel_time:.4f}s")
        print(f"Speedup:           {speedup:.3f}x")

        assert sequential_time >= MIN_EXPECTED_MEDIAN_RUNTIME
        assert parallel_time >= 0.0
        assert speedup >= 1.35
