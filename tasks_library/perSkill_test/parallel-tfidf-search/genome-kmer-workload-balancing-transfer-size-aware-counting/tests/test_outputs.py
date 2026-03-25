#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from kmer_counter_baseline import count_kmers_sequential, discover_fasta_paths, run_naive_equal_split

BALANCED_MODULE_PATH = Path("/root/workspace/kmer_counter_balanced.py")
ELAPSED_RATIO_TARGET = 0.85
LOAD_SPREAD_RATIO_TARGET = 0.25


def load_balanced_module():
    if not BALANCED_MODULE_PATH.exists():
        pytest.fail("/root/workspace/kmer_counter_balanced.py 不存在")

    spec = importlib.util.spec_from_file_location("kmer_counter_balanced", BALANCED_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def base_spread(report: dict) -> int:
    base_loads = [worker["base_load"] for worker in report["worker_stats"]]
    return max(base_loads) - min(base_loads)


@pytest.fixture(scope="session")
def fasta_paths():
    return discover_fasta_paths()


def test_module_contract():
    module = load_balanced_module()
    assert hasattr(module, "count_kmers_balanced")


def test_counts_match_sequential(fasta_paths, tmp_path):
    module = load_balanced_module()
    sequential_output = tmp_path / "sequential_counts.json"
    sequential_report = tmp_path / "sequential_report.json"
    balanced_output = tmp_path / "balanced_counts.json"
    balanced_report = tmp_path / "balanced_report.json"

    count_kmers_sequential(
        fasta_paths=fasta_paths,
        k=6,
        output_path=str(sequential_output),
        report_path=str(sequential_report),
    )
    report = module.count_kmers_balanced(
        fasta_paths=fasta_paths,
        k=6,
        output_path=str(balanced_output),
        report_path=str(balanced_report),
        num_workers=2,
    )

    expected_payload = read_json(sequential_output)
    actual_payload = read_json(balanced_output)
    saved_report = read_json(balanced_report)

    assert actual_payload == expected_payload
    assert report == saved_report
    assert report["k"] == 6
    assert report["num_workers"] == 2
    assert report["total_sequences"] == expected_payload["total_sequences"]
    assert report["total_bases"] > 3_000_000
    assert report["distinct_kmers"] == len(expected_payload["counts"])
    assert len(report["worker_stats"]) == 2

    for worker_id, worker in enumerate(report["worker_stats"]):
        assert worker["worker_id"] == worker_id
        assert worker["sequence_count"] > 0
        assert worker["base_load"] > 0
        assert worker["kmers_emitted"] >= worker["sequence_count"]


def test_base_load_is_more_balanced(fasta_paths, tmp_path):
    module = load_balanced_module()

    naive_report = run_naive_equal_split(
        fasta_paths=fasta_paths,
        k=6,
        output_path=str(tmp_path / "naive_counts.json"),
        report_path=str(tmp_path / "naive_report.json"),
        num_workers=2,
    )
    balanced_report = module.count_kmers_balanced(
        fasta_paths=fasta_paths,
        k=6,
        output_path=str(tmp_path / "balanced_counts.json"),
        report_path=str(tmp_path / "balanced_report.json"),
        num_workers=2,
    )

    naive_spread = base_spread(naive_report)
    balanced_spread = base_spread(balanced_report)

    assert naive_spread > 0
    assert balanced_spread < naive_spread
    assert balanced_spread / naive_spread <= LOAD_SPREAD_RATIO_TARGET, (
        f"base load spread 改善不足: naive={naive_spread}, balanced={balanced_spread}"
    )


def _measure_runner(runner, fasta_paths, tmp_path, prefix):
    runner(
        fasta_paths=fasta_paths,
        k=6,
        output_path=str(tmp_path / f"{prefix}_warmup_counts.json"),
        report_path=str(tmp_path / f"{prefix}_warmup_report.json"),
        num_workers=2,
    )

    elapsed_runs = []
    for attempt in range(3):
        start_time = time.perf_counter()
        runner(
            fasta_paths=fasta_paths,
            k=6,
            output_path=str(tmp_path / f"{prefix}_{attempt}_counts.json"),
            report_path=str(tmp_path / f"{prefix}_{attempt}_report.json"),
            num_workers=2,
        )
        elapsed_runs.append(time.perf_counter() - start_time)
    return elapsed_runs


def test_balanced_beats_naive_runtime(fasta_paths, tmp_path):
    module = load_balanced_module()

    naive_elapsed = _measure_runner(run_naive_equal_split, fasta_paths, tmp_path, "naive")
    balanced_elapsed = _measure_runner(module.count_kmers_balanced, fasta_paths, tmp_path, "balanced")

    wins = sum(1 for naive, balanced in zip(naive_elapsed, balanced_elapsed) if balanced < naive)
    ratio = statistics.median(balanced_elapsed) / statistics.median(naive_elapsed)

    assert wins >= 2, f"平衡版只有 {wins}/3 次快于朴素版: naive={naive_elapsed}, balanced={balanced_elapsed}"
    assert ratio <= ELAPSED_RATIO_TARGET, (
        f"总耗时中位数比例过高: ratio={ratio:.3f}, "
        f"naive={naive_elapsed}, balanced={balanced_elapsed}"
    )
