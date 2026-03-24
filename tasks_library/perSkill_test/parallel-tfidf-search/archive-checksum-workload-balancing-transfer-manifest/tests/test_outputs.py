#!/usr/bin/env python3
"""
Tests for the archive checksum manifest transfer task.
"""

from __future__ import annotations

import hashlib
import importlib
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from archive_fixture_builder import build_skewed_archive
from sequential_manifest import build_checksum_manifest_sequential


def manifest_signature(manifest):
    return [
        (
            entry.relative_path,
            entry.size_bytes,
            entry.sha256,
            entry.block_digest,
        )
        for entry in manifest.entries
    ]


class TestParallelManifestModule:
    def test_parallel_solution_exists(self):
        try:
            from checksum_balance_solution import build_checksum_manifest_parallel  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"Could not import checksum_balance_solution: {exc}")


class TestCorrectness:
    @pytest.fixture(scope="class")
    def sample_root(self):
        return Path("/root/workspace/sample_archive")

    def test_sample_archive_matches_baseline(self, sample_root):
        from checksum_balance_solution import build_checksum_manifest_parallel

        sequential = build_checksum_manifest_sequential(sample_root)
        parallel = build_checksum_manifest_parallel(sample_root, num_workers=4, chunk_size=2)

        assert parallel.num_files == sequential.num_files
        assert parallel.total_size_bytes == sequential.total_size_bytes
        assert manifest_signature(parallel.manifest) == manifest_signature(sequential.manifest)

    def test_parallel_order_is_stable(self):
        from checksum_balance_solution import build_checksum_manifest_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_root = build_skewed_archive(Path(tmpdir) / "archive", seed=11, small_count=32, medium_count=6, large_count=3, giant_count=1)

            sequential = build_checksum_manifest_sequential(archive_root)
            parallel_a = build_checksum_manifest_parallel(archive_root, num_workers=4, chunk_size=3)
            parallel_b = build_checksum_manifest_parallel(archive_root, num_workers=3, chunk_size=5)

            expected_paths = [entry.relative_path for entry in sequential.manifest.entries]
            assert expected_paths == sorted(expected_paths)
            assert manifest_signature(parallel_a.manifest) == manifest_signature(sequential.manifest)
            assert manifest_signature(parallel_b.manifest) == manifest_signature(sequential.manifest)


class TestPerformance:
    def test_parallel_is_faster_on_skewed_archive(self, monkeypatch):
        checksum_balance_solution = importlib.import_module("checksum_balance_solution")
        build_checksum_manifest_parallel = checksum_balance_solution.build_checksum_manifest_parallel

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_root = build_skewed_archive(
                Path(tmpdir) / "archive",
                seed=23,
                small_count=160,
                medium_count=16,
                large_count=8,
                giant_count=2,
            )

            def synthetic_hash_file(path, block_size=256 * 1024):
                size_bytes = Path(path).stat().st_size
                payload = f"{Path(path).resolve()}::{size_bytes}::{block_size}".encode("utf-8")
                time.sleep(size_bytes / 20_000_000)
                return (
                    hashlib.sha256(payload).hexdigest(),
                    hashlib.blake2b(payload, digest_size=20).hexdigest(),
                )

            monkeypatch.setattr("sequential_manifest.hash_file", synthetic_hash_file)
            monkeypatch.setattr(checksum_balance_solution, "hash_file", synthetic_hash_file, raising=False)

            start = time.perf_counter()
            sequential = build_checksum_manifest_sequential(archive_root)
            seq_time = time.perf_counter() - start

            start = time.perf_counter()
            parallel = build_checksum_manifest_parallel(archive_root, num_workers=4, chunk_size=8)
            para_time = time.perf_counter() - start

            speedup = seq_time / para_time
            print("\nArchive Manifest Synthetic Performance:")
            print(f"  Sequential: {seq_time:.3f}s")
            print(f"  Parallel:   {para_time:.3f}s")
            print(f"  Speedup:    {speedup:.2f}x")

            assert manifest_signature(parallel.manifest) == manifest_signature(sequential.manifest)
            assert speedup >= 1.15, f"Insufficient speedup: {speedup:.2f}x (required: 1.15x)"
