#!/bin/bash
set -euo pipefail

cat > /root/workspace/memory_search_solution.py <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import heapq
import json
import math
from pathlib import Path

from archive_search_baseline import compute_term_frequencies, load_queries, tokenize


def _iter_corpus(path: str):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _worst_key(item):
    score, doc_id, _headline = item
    return (score, -doc_id)


def _push_top_k(heap, candidate, top_k):
    if len(heap) < top_k:
        heapq.heappush(heap, candidate)
        return
    if _worst_key(candidate) > _worst_key(heap[0]):
        heapq.heapreplace(heap, candidate)


def compute_stats(corpus_path: str):
    document_frequencies: dict[str, int] = {}
    num_documents = 0
    num_postings = 0

    for row in _iter_corpus(corpus_path):
        num_documents += 1
        tokens = tokenize(f"{row['headline']} {row['body']}")
        tf = compute_term_frequencies(tokens)
        num_postings += len(tf)
        for term in tf:
            document_frequencies[term] = document_frequencies.get(term, 0) + 1

    idf = {term: math.log(num_documents / df) + 1 for term, df in document_frequencies.items()}
    return {
        "num_documents": num_documents,
        "vocabulary_size": len(document_frequencies),
        "num_postings": num_postings,
        "idf": idf,
    }


def generate_report(corpus_path: str, queries_path: str, top_k: int = 5):
    stats = compute_stats(corpus_path)
    idf = stats["idf"]
    query_rows = load_queries(queries_path)

    prepared_queries = []
    for query_row in query_rows:
        query_tf = compute_term_frequencies(tokenize(query_row["query"]))
        query_vector = {term: tf * idf[term] for term, tf in query_tf.items() if term in idf}
        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        prepared_queries.append(
            {
                "query_id": query_row["query_id"],
                "query": query_row["query"],
                "vector": query_vector,
                "norm": query_norm,
                "heap": [],
            }
        )

    for row in _iter_corpus(corpus_path):
        tf = compute_term_frequencies(tokenize(f"{row['headline']} {row['body']}"))
        if not tf:
            continue

        weighted_terms = {}
        norm_squared = 0.0
        for term, term_tf in tf.items():
            value = term_tf * idf[term]
            weighted_terms[term] = value
            norm_squared += value * value
        doc_norm = math.sqrt(norm_squared)
        if doc_norm == 0.0:
            continue

        doc_id = int(row["doc_id"])
        headline = str(row["headline"])
        for prepared in prepared_queries:
            query_vector = prepared["vector"]
            if not query_vector or prepared["norm"] == 0.0:
                continue
            dot = 0.0
            for term, query_value in query_vector.items():
                doc_value = weighted_terms.get(term)
                if doc_value is not None:
                    dot += query_value * doc_value
            if dot <= 0.0:
                continue
            score = dot / (prepared["norm"] * doc_norm)
            _push_top_k(prepared["heap"], (score, doc_id, headline), top_k)

    query_results = []
    for prepared in prepared_queries:
        ranked = sorted(prepared["heap"], key=lambda item: (-item[0], item[1]))
        query_results.append(
            {
                "query_id": prepared["query_id"],
                "query": prepared["query"],
                "results": [
                    {
                        "doc_id": doc_id,
                        "headline": headline,
                        "score": round(score, 12),
                    }
                    for score, doc_id, headline in ranked
                ],
            }
        )

    return {
        "corpus": {
            "num_documents": stats["num_documents"],
            "vocabulary_size": stats["vocabulary_size"],
            "num_postings": stats["num_postings"],
        },
        "queries": query_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory-bounded archive search.")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    report = generate_report(args.corpus, args.queries, args.top_k)
    with Path(args.output).open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
PY

chmod +x /root/workspace/memory_search_solution.py
