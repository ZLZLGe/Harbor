#!/usr/bin/env python3
"""Verifier for the streaming TF-IDF archive task."""

from __future__ import annotations

import json
import tracemalloc
from pathlib import Path
import sys

import pytest

if "/root/workspace" not in sys.path:
    sys.path.insert(0, "/root/workspace")

from archive_common import SearchHit, take_best_ids
from archive_index_baseline import batch_search_baseline, build_archive_index_baseline
from bulletin_corpus import write_bulletin_jsonl


def load_solution():
    import importlib.util
    import sys

    solution_path = Path("/root/workspace/streaming_tfidf_solution.py")
    if not solution_path.exists():
        pytest.fail("missing /root/workspace/streaming_tfidf_solution.py")

    spec = importlib.util.spec_from_file_location("streaming_tfidf_solution", solution_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["streaming_tfidf_solution"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def solution():
    return load_solution()


@pytest.fixture(scope="session")
def generated_queries():
    payload = json.loads(Path("/root/workspace/query_workload.json").read_text(encoding="utf-8"))
    return payload["generated_queries"]


@pytest.fixture(scope="session")
def asset_queries():
    payload = json.loads(Path("/root/workspace/query_workload.json").read_text(encoding="utf-8"))
    return payload["asset_queries"]


@pytest.fixture(scope="session")
def sample_asset_path():
    return "/root/workspace/sample_bulletins.jsonl"


@pytest.fixture(scope="session")
def small_generated_corpus(tmp_path_factory):
    path = tmp_path_factory.mktemp("corpora") / "small.jsonl"
    write_bulletin_jsonl(path, num_records=160, seed=17)
    return str(path)


@pytest.fixture(scope="session")
def medium_generated_corpus(tmp_path_factory):
    path = tmp_path_factory.mktemp("corpora") / "medium.jsonl"
    write_bulletin_jsonl(path, num_records=3200, seed=91)
    return str(path)


def summarize_hits(rows: list[list[SearchHit]]):
    return [[(hit.doc_id, round(hit.score, 10)) for hit in row] for row in rows]


def measure_peak_bytes(builder, corpus_path):
    tracemalloc.start()
    try:
        result = builder(corpus_path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


class TestSolutionShape:
    def test_module_exports_required_functions(self, solution):
        assert hasattr(solution, "build_streaming_tfidf_index")
        assert hasattr(solution, "batch_search_streaming")


class TestExactness:
    def test_generated_corpus_matches_baseline(self, solution, small_generated_corpus, generated_queries):
        baseline = build_archive_index_baseline(small_generated_corpus)
        candidate = solution.build_streaming_tfidf_index(small_generated_corpus)

        assert candidate.num_documents == baseline.num_documents
        assert candidate.vocabulary_size == baseline.vocabulary_size
        assert candidate.index.num_documents == baseline.index.num_documents
        assert set(candidate.index.vocabulary) == baseline.index.vocabulary
        assert candidate.index.document_frequencies == baseline.index.document_frequencies

        expected = batch_search_baseline(generated_queries, baseline.index, top_k=5)
        actual = solution.batch_search_streaming(generated_queries, candidate.index, top_k=5)
        assert summarize_hits(actual) == summarize_hits(expected)

    def test_sample_asset_returns_expected_documents(self, solution, sample_asset_path, asset_queries):
        result = solution.build_streaming_tfidf_index(sample_asset_path)
        rows = solution.batch_search_streaming(asset_queries, result.index, top_k=3)
        assert take_best_ids(rows) == [
            [5, 0],
            [1],
            [4, 1],
            [3],
        ]

    def test_postings_structure_is_exposed(self, solution, sample_asset_path):
        result = solution.build_streaming_tfidf_index(sample_asset_path)
        posting = result.index.postings["relay"]
        assert hasattr(posting, "doc_ids")
        assert hasattr(posting, "weights")
        assert len(posting.doc_ids) == len(posting.weights)


class TestMemoryBudget:
    def test_peak_memory_is_substantially_lower_than_baseline(
        self,
        solution,
        medium_generated_corpus,
        generated_queries,
    ):
        baseline_result, baseline_peak = measure_peak_bytes(build_archive_index_baseline, medium_generated_corpus)
        candidate_result, candidate_peak = measure_peak_bytes(solution.build_streaming_tfidf_index, medium_generated_corpus)

        expected = batch_search_baseline(generated_queries, baseline_result.index, top_k=5)
        actual = solution.batch_search_streaming(generated_queries, candidate_result.index, top_k=5)
        assert summarize_hits(actual) == summarize_hits(expected)

        assert candidate_peak < baseline_peak * 0.65, (
            f"candidate peak {candidate_peak} not below 65% of baseline peak {baseline_peak}"
        )
        assert candidate_peak < 45 * 1024 * 1024, f"candidate peak too high: {candidate_peak} bytes"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
