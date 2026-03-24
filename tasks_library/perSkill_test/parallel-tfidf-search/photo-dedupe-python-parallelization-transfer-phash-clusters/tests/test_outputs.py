#!/usr/bin/env python3
"""
Tests for the parallel photo dedupe transfer task.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

import pytest

WORKSPACE_DIR = Path(os.environ.get("TASK_WORKSPACE", "/root/workspace"))
sys.path.insert(0, str(WORKSPACE_DIR))

from photo_fixture import (
    expected_groups_from_specs,
    generate_album_blueprint,
    load_album_blueprint,
    materialize_album,
    materialize_album_from_blueprint,
)
from sequential_photo_dedupe import build_photo_index_sequential, run_photo_dedupe_sequential


BLUEPRINT_PATH = WORKSPACE_DIR / "album_blueprints.json"


def _normalize_clusters(report: dict) -> list[list[str]]:
    return sorted([sorted(cluster["members"]) for cluster in report["clusters"]], key=lambda members: members[0])


class TestParallelModule:
    def test_parallel_solution_exists(self) -> None:
        try:
            from parallel_photo_dedupe import build_photo_index_parallel, run_photo_dedupe_parallel  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"Could not import parallel_photo_dedupe: {exc}")


class TestCorrectness:
    def test_hash_records_match_sequential(self, tmp_path: Path) -> None:
        from parallel_photo_dedupe import build_photo_index_parallel

        album_dir = tmp_path / "sample_album"
        materialize_album_from_blueprint(BLUEPRINT_PATH, album_dir)

        sequential = build_photo_index_sequential(str(album_dir), hash_size=8)
        parallel = build_photo_index_parallel(str(album_dir), hash_size=8, num_workers=4, chunk_size=3)

        seq_records = [
            (record.photo_id, record.hash_bits, record.hash_value, record.width, record.height, record.mean_luma)
            for record in sequential.index.photo_records
        ]
        parallel_records = [
            (record.photo_id, record.hash_bits, record.hash_value, record.width, record.height, record.mean_luma)
            for record in parallel.index.photo_records
        ]

        assert seq_records == parallel_records

    def test_duplicate_clusters_match_expected_blueprint(self, tmp_path: Path) -> None:
        from parallel_photo_dedupe import run_photo_dedupe_parallel

        specs = load_album_blueprint(BLUEPRINT_PATH)
        album_dir = tmp_path / "cluster_album"
        materialize_album(specs, album_dir)

        sequential_report = run_photo_dedupe_sequential(str(album_dir), hash_size=8, max_hamming_distance=18)
        parallel_report = run_photo_dedupe_parallel(
            str(album_dir),
            hash_size=8,
            max_hamming_distance=18,
            num_workers=4,
            chunk_size=4,
        )

        assert parallel_report["ordered_photo_ids"] == sequential_report["ordered_photo_ids"]
        assert parallel_report["duplicate_photo_count"] == sequential_report["duplicate_photo_count"]
        assert parallel_report["unique_photo_count"] == sequential_report["unique_photo_count"]
        assert _normalize_clusters(parallel_report) == _normalize_clusters(sequential_report)
        assert _normalize_clusters(parallel_report) == expected_groups_from_specs(specs)

        assert parallel_report["cluster_count"] == 3
        assert parallel_report["duplicate_photo_count"] == 8
        assert parallel_report["unique_photo_count"] == 2
        assert parallel_report["clusters"][0]["anchor"] == "gantry_crane_00"


class TestPerformance:
    @pytest.fixture(scope="class")
    def performance_album(self, tmp_path_factory: pytest.TempPathFactory) -> str:
        album_dir = tmp_path_factory.mktemp("perf_album")
        specs = generate_album_blueprint(num_groups=24, variants_per_group=4, seed=20260322, width=160, height=160)
        materialize_album(specs, album_dir)
        return str(album_dir)

    def test_parallel_index_speedup(self, performance_album: str) -> None:
        from parallel_photo_dedupe import build_photo_index_parallel

        seq_durations = []
        para_durations = []

        for _ in range(2):
            start = time.perf_counter()
            build_photo_index_sequential(performance_album, hash_size=12)
            seq_durations.append(time.perf_counter() - start)

            start = time.perf_counter()
            build_photo_index_parallel(performance_album, hash_size=12, num_workers=4, chunk_size=12)
            para_durations.append(time.perf_counter() - start)

        seq_median = statistics.median(seq_durations)
        para_median = statistics.median(para_durations)
        speedup = seq_median / para_median

        print(f"\nSequential median: {seq_median:.3f}s")
        print(f"Parallel median:   {para_median:.3f}s")
        print(f"Speedup:           {speedup:.2f}x")

        assert speedup >= 1.35, f"Parallel build speedup too low: {speedup:.2f}x"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
