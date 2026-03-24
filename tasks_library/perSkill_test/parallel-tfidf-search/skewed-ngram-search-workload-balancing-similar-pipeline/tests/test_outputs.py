#!/usr/bin/env python3
"""
Tests for the skewed n-gram parallel search task.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

WORKSPACE_DIR = Path(os.environ.get("TASK_WORKSPACE", "/root/workspace"))
sys.path.insert(0, str(WORKSPACE_DIR))

from ngram_support_corpus import generate_query_batch, generate_support_corpus
from sequential_ngram import batch_search_sequential, build_ngram_index_sequential


class TestParallelInterface:
    def test_parallel_solution_exists(self):
        try:
            from ngram_parallel_solution import batch_search_parallel, build_ngram_index_parallel  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"Could not import ngram_parallel_solution: {exc}")


class TestCorrectness:
    @pytest.fixture(scope="class")
    def small_corpus(self):
        return generate_support_corpus(140, seed=17, long_doc_ratio=0.2)

    @pytest.fixture(scope="class")
    def sequential_index(self, small_corpus):
        return build_ngram_index_sequential(small_corpus, n=3)

    def test_index_statistics_match(self, small_corpus, sequential_index):
        from ngram_parallel_solution import build_ngram_index_parallel

        parallel_result = build_ngram_index_parallel(small_corpus, n=3, num_workers=4, chunk_size=12)

        assert parallel_result.num_documents == sequential_index.num_documents
        assert parallel_result.vocabulary_size == sequential_index.vocabulary_size
        assert parallel_result.index.n == sequential_index.index.n
        assert parallel_result.index.vocabulary == sequential_index.index.vocabulary

        sample_grams = sorted(sequential_index.index.vocabulary)[:80]
        for gram in sample_grams:
            assert parallel_result.index.document_frequencies[gram] == sequential_index.index.document_frequencies[gram]
            assert abs(parallel_result.index.idf[gram] - sequential_index.index.idf[gram]) < 1e-12
            assert parallel_result.index.inverted_index[gram] == sequential_index.index.inverted_index[gram]

    def test_search_results_match(self, small_corpus, sequential_index):
        from ngram_parallel_solution import batch_search_parallel, build_ngram_index_parallel

        parallel_index = build_ngram_index_parallel(small_corpus, n=3, num_workers=4, chunk_size=12)
        queries = [
            "beacon pay recipt mismatch",
            "nova mail attch render glitch",
            "harbor desk refund aproval deadlock",
            "lumen mobile offlne sync drift",
            "quarry ops device enrolment failur",
        ]
        queries.extend(generate_query_batch(small_corpus, 20, seed=23))

        sequential_results = batch_search_sequential(queries, sequential_index.index, top_k=6, documents=small_corpus)
        parallel_results, elapsed_time = batch_search_parallel(
            queries,
            parallel_index.index,
            top_k=6,
            num_workers=4,
            documents=small_corpus,
        )

        assert elapsed_time >= 0.0
        assert len(sequential_results) == len(parallel_results)

        for query_idx, (expected, actual) in enumerate(zip(sequential_results, parallel_results)):
            assert len(expected) == len(actual), f"Different result count for query {query_idx}"
            for rank, (expected_hit, actual_hit) in enumerate(zip(expected, actual)):
                assert expected_hit.doc_id == actual_hit.doc_id, f"Doc mismatch at query {query_idx}, rank {rank}"
                assert abs(expected_hit.score - actual_hit.score) < 1e-12, f"Score mismatch at query {query_idx}, rank {rank}"
                assert expected_hit.title == actual_hit.title


class TestPerformance:
    @pytest.fixture(scope="class")
    def performance_corpus(self):
        return generate_support_corpus(420, seed=91, long_doc_ratio=0.22)

    def test_index_build_speedup(self, performance_corpus):
        from ngram_parallel_solution import build_ngram_index_parallel

        start = time.perf_counter()
        build_ngram_index_sequential(performance_corpus, n=3)
        sequential_time = time.perf_counter() - start

        start = time.perf_counter()
        build_ngram_index_parallel(performance_corpus, n=3, num_workers=4, chunk_size=18)
        parallel_time = time.perf_counter() - start

        speedup = sequential_time / parallel_time

        print("\nIndex build timing:")
        print(f"  Sequential: {sequential_time:.3f}s")
        print(f"  Parallel:   {parallel_time:.3f}s")
        print(f"  Speedup:    {speedup:.2f}x")

        assert speedup >= 1.05, f"Expected at least 1.05x speedup, got {speedup:.2f}x"

    def test_batch_search_speedup(self, performance_corpus):
        from ngram_parallel_solution import batch_search_parallel, build_ngram_index_parallel

        parallel_index = build_ngram_index_parallel(performance_corpus, n=3, num_workers=4, chunk_size=18)
        queries = generate_query_batch(performance_corpus, 260, seed=123)

        start = time.perf_counter()
        batch_search_sequential(queries, parallel_index.index, top_k=8, documents=performance_corpus)
        sequential_time = time.perf_counter() - start

        start = time.perf_counter()
        _results, parallel_time = batch_search_parallel(
            queries,
            parallel_index.index,
            top_k=8,
            num_workers=4,
            documents=performance_corpus,
        )
        outer_parallel_time = time.perf_counter() - start

        speedup = sequential_time / parallel_time

        print("\nBatch search timing:")
        print(f"  Sequential: {sequential_time:.3f}s")
        print(f"  Parallel(inner): {parallel_time:.3f}s")
        print(f"  Parallel(outer): {outer_parallel_time:.3f}s")
        print(f"  Speedup:    {speedup:.2f}x")

        assert speedup >= 1.08, f"Expected at least 1.08x speedup, got {speedup:.2f}x"
