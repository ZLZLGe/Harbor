#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from archive_fixture import write_corpus
from archive_search_baseline import compute_term_frequencies, load_queries, tokenize


SOLUTION_PATH = Path("/root/workspace/memory_search_solution.py")
QUERIES_PATH = Path("/root/workspace/archive_queries.json")
TOP_K = 5
MEMORY_LIMIT_MB = 350
RSS_PATTERN = re.compile(r"Maximum resident set size \(kbytes\):\s+(\d+)")


def run_solution(corpus_path: Path, output_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            str(SOLUTION_PATH),
            "--corpus",
            str(corpus_path),
            "--queries",
            str(QUERIES_PATH),
            "--output",
            str(output_path),
            "--top-k",
            str(TOP_K),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    with output_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def oracle_report(corpus_path: Path):
    queries = load_queries(QUERIES_PATH)
    document_frequencies: dict[str, int] = defaultdict(int)
    num_documents = 0
    num_postings = 0

    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tf = compute_term_frequencies(tokenize(f"{row['headline']} {row['body']}"))
            num_documents += 1
            num_postings += len(tf)
            for term in tf:
                document_frequencies[term] += 1

    idf = {term: math.log(num_documents / df) + 1 for term, df in document_frequencies.items()}
    prepared_queries = []
    for query in queries:
        query_tf = compute_term_frequencies(tokenize(query["query"]))
        query_vector = {term: tf * idf[term] for term, tf in query_tf.items() if term in idf}
        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        prepared_queries.append(
            {
                "query_id": query["query_id"],
                "query": query["query"],
                "vector": query_vector,
                "norm": query_norm,
                "scores": [],
            }
        )

    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tf = compute_term_frequencies(tokenize(f"{row['headline']} {row['body']}"))
            weighted_terms = {term: term_tf * idf[term] for term, term_tf in tf.items()}
            doc_norm = math.sqrt(sum(value * value for value in weighted_terms.values()))
            if doc_norm == 0.0:
                continue
            doc_id = int(row["doc_id"])
            headline = str(row["headline"])
            for query in prepared_queries:
                if not query["vector"] or query["norm"] == 0.0:
                    continue
                dot = sum(query["vector"].get(term, 0.0) * weighted_terms.get(term, 0.0) for term in query["vector"])
                if dot > 0.0:
                    query["scores"].append((doc_id, headline, dot / (query["norm"] * doc_norm)))

    return {
        "corpus": {
            "num_documents": num_documents,
            "vocabulary_size": len(document_frequencies),
            "num_postings": num_postings,
        },
        "queries": [
            {
                "query_id": query["query_id"],
                "query": query["query"],
                "results": [
                    {
                        "doc_id": doc_id,
                        "headline": headline,
                        "score": round(score, 12),
                    }
                    for doc_id, headline, score in sorted(query["scores"], key=lambda item: (-item[2], item[0]))[:TOP_K]
                ],
            }
            for query in prepared_queries
        ],
    }


def baseline_report(corpus_path: Path):
    output_path = corpus_path.parent / "baseline_report.json"
    subprocess.run(
        [
            sys.executable,
            "/root/workspace/archive_search_baseline.py",
            "--corpus",
            str(corpus_path),
            "--queries",
            str(QUERIES_PATH),
            "--output",
            str(output_path),
            "--top-k",
            str(TOP_K),
        ],
        check=True,
    )
    with output_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_solution_file_exists():
    assert SOLUTION_PATH.exists(), "missing /root/workspace/memory_search_solution.py"


def test_matches_baseline_on_small_fixture(tmp_path: Path):
    corpus_path = tmp_path / "small_archive.jsonl"
    output_path = tmp_path / "small_report.json"
    write_corpus(corpus_path, num_docs=1200, seed=11)

    produced = run_solution(corpus_path, output_path)
    expected = baseline_report(corpus_path)
    assert produced == expected


def test_report_contract_and_large_fixture_correctness(tmp_path: Path):
    corpus_path = tmp_path / "full_archive.jsonl"
    output_path = tmp_path / "full_report.json"
    write_corpus(corpus_path, num_docs=18000, seed=29)

    produced = run_solution(corpus_path, output_path)
    expected = oracle_report(corpus_path)

    assert produced == expected
    assert set(produced) == {"corpus", "queries"}
    assert set(produced["corpus"]) == {"num_documents", "vocabulary_size", "num_postings"}
    assert len(produced["queries"]) == len(load_queries(QUERIES_PATH))
    for query_row in produced["queries"]:
        assert set(query_row) == {"query_id", "query", "results"}
        for result in query_row["results"]:
            assert set(result) == {"doc_id", "headline", "score"}
            assert isinstance(result["doc_id"], int)
            assert isinstance(result["headline"], str)
            assert isinstance(result["score"], float)


def test_memory_budget_on_full_fixture(tmp_path: Path):
    corpus_path = tmp_path / "memory_archive.jsonl"
    output_path = tmp_path / "memory_report.json"
    write_corpus(corpus_path, num_docs=18000, seed=29)

    completed = subprocess.run(
        [
            "/usr/bin/time",
            "-v",
            sys.executable,
            str(SOLUTION_PATH),
            "--corpus",
            str(corpus_path),
            "--queries",
            str(QUERIES_PATH),
            "--output",
            str(output_path),
            "--top-k",
            str(TOP_K),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    match = RSS_PATTERN.search(completed.stderr)
    assert match, completed.stderr
    rss_mb = int(match.group(1)) / 1024
    assert rss_mb <= MEMORY_LIMIT_MB, f"peak RSS {rss_mb:.1f} MB exceeds {MEMORY_LIMIT_MB} MB"
