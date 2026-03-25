#!/usr/bin/env python3

import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from mock_shard_api import running_server
from naive_ingest_baseline import run_naive_round_robin

BALANCED_MODULE_PATH = Path("/root/workspace/balanced_ingest.py")
ELAPSED_RATIO_TARGET = 0.88
SPREAD_RATIO_TARGET = 0.80


def load_balanced_module():
    if not BALANCED_MODULE_PATH.exists():
        pytest.fail("/root/workspace/balanced_ingest.py 不存在")

    spec = importlib.util.spec_from_file_location("balanced_ingest", BALANCED_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_ndjson(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def busy_spread(report):
    busy_times = [worker["busy_seconds"] for worker in report["worker_stats"]]
    return max(busy_times) - min(busy_times)


@pytest.fixture(scope="session")
def service():
    with running_server() as context:
        yield context


@pytest.fixture(scope="session")
def expected_records(service):
    return sorted(service["fixture"]["all_records"], key=lambda item: item["record_id"])


def test_module_contract():
    module = load_balanced_module()
    assert hasattr(module, "run_balanced_ingest")


def test_output_correctness(service, expected_records, tmp_path):
    module = load_balanced_module()
    output_path = tmp_path / "balanced.ndjson"
    report_path = tmp_path / "balanced_report.json"

    report = module.run_balanced_ingest(
        service["base_url"],
        output_path=str(output_path),
        report_path=str(report_path),
        num_workers=4,
    )

    assert output_path.exists()
    assert report_path.exists()

    records = read_ndjson(output_path)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert records == expected_records
    assert [record["record_id"] for record in records] == sorted(record["record_id"] for record in records)
    assert report == saved_report
    assert report["num_workers"] == 4
    assert report["total_records"] == len(expected_records)
    assert report["total_pages"] == service["fixture"]["total_pages"]
    assert len(report["worker_stats"]) == 4
    assert sum(worker["requests"] for worker in report["worker_stats"]) == service["fixture"]["total_pages"]

    for worker_id, worker in enumerate(report["worker_stats"]):
        assert worker["worker_id"] == worker_id
        assert worker["requests"] >= 0
        assert worker["busy_seconds"] >= 0.0


def _measure_runner(runner, base_url, tmp_path, prefix):
    elapsed_runs = []
    spread_runs = []

    runner(
        base_url,
        output_path=str(tmp_path / f"{prefix}_warmup.ndjson"),
        report_path=str(tmp_path / f"{prefix}_warmup.json"),
        num_workers=4,
    )

    for attempt in range(3):
        output_path = tmp_path / f"{prefix}_{attempt}.ndjson"
        report_path = tmp_path / f"{prefix}_{attempt}.json"
        started = time.perf_counter()
        report = runner(
            base_url,
            output_path=str(output_path),
            report_path=str(report_path),
            num_workers=4,
        )
        elapsed_runs.append(time.perf_counter() - started)
        spread_runs.append(busy_spread(report))

    return elapsed_runs, spread_runs


def test_balanced_beats_naive(service, tmp_path):
    module = load_balanced_module()

    naive_elapsed, naive_spread = _measure_runner(
        run_naive_round_robin,
        service["base_url"],
        tmp_path,
        "naive",
    )
    balanced_elapsed, balanced_spread = _measure_runner(
        module.run_balanced_ingest,
        service["base_url"],
        tmp_path,
        "balanced",
    )

    elapsed_wins = sum(1 for naive, balanced in zip(naive_elapsed, balanced_elapsed) if balanced < naive)
    elapsed_ratio = statistics.median(balanced_elapsed) / statistics.median(naive_elapsed)
    spread_ratio = statistics.median(balanced_spread) / statistics.median(naive_spread)

    assert elapsed_wins >= 2, (
        f"平衡版只有 {elapsed_wins}/3 次快于朴素轮询版: "
        f"naive={naive_elapsed}, balanced={balanced_elapsed}"
    )
    assert elapsed_ratio <= ELAPSED_RATIO_TARGET, (
        f"总耗时中位数比例过高: {elapsed_ratio:.3f}, "
        f"naive={naive_elapsed}, balanced={balanced_elapsed}"
    )
    assert spread_ratio <= SPREAD_RATIO_TARGET, (
        f"worker busy spread 中位数比例过高: {spread_ratio:.3f}, "
        f"naive={naive_spread}, balanced={balanced_spread}"
    )
