#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path


TOKEN_PATTERN = re.compile(r"\b[a-z]{2,}\b")
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "then",
        "there",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOP_WORDS]


def compute_term_frequencies(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts: dict[str, int] = defaultdict(int)
    for token in tokens:
        counts[token] += 1
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def load_corpus(path: str | Path) -> list[dict[str, object]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def load_queries(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def build_index(corpus: list[dict[str, object]]) -> dict[str, object]:
    num_documents = len(corpus)
    vocabulary: set[str] = set()
    document_frequencies: dict[str, int] = defaultdict(int)
    doc_term_freqs: dict[int, dict[str, float]] = {}
    doc_vectors: dict[int, dict[str, float]] = {}
    doc_norms: dict[int, float] = {}
    inverted_index: dict[str, list[tuple[int, float]]] = defaultdict(list)
    doc_headlines: dict[int, str] = {}
    num_postings = 0

    for row in corpus:
        doc_id = int(row["doc_id"])
        doc_headlines[doc_id] = str(row["headline"])
        text = f"{row['headline']} {row['body']}"
        tokens = tokenize(text)
        tf = compute_term_frequencies(tokens)
        doc_term_freqs[doc_id] = tf
        unique_terms = set(tf)
        num_postings += len(unique_terms)
        vocabulary.update(unique_terms)
        for term in unique_terms:
            document_frequencies[term] += 1

    idf = {term: math.log(num_documents / df) + 1 for term, df in document_frequencies.items()}

    for doc_id, tf in doc_term_freqs.items():
        vector: dict[str, float] = {}
        norm_squared = 0.0
        for term, term_tf in tf.items():
            value = term_tf * idf[term]
            vector[term] = value
            norm_squared += value * value
            inverted_index[term].append((doc_id, value))
        doc_vectors[doc_id] = vector
        doc_norms[doc_id] = math.sqrt(norm_squared)

    for postings in inverted_index.values():
        postings.sort(key=lambda item: (-item[1], item[0]))

    return {
        "num_documents": num_documents,
        "vocabulary_size": len(vocabulary),
        "num_postings": num_postings,
        "idf": idf,
        "doc_vectors": doc_vectors,
        "doc_norms": doc_norms,
        "headlines": doc_headlines,
    }


def search_queries(
    queries: list[dict[str, str]],
    index: dict[str, object],
    top_k: int,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    idf: dict[str, float] = index["idf"]  # type: ignore[assignment]
    doc_vectors: dict[int, dict[str, float]] = index["doc_vectors"]  # type: ignore[assignment]
    doc_norms: dict[int, float] = index["doc_norms"]  # type: ignore[assignment]
    headlines: dict[int, str] = index["headlines"]  # type: ignore[assignment]

    for query_row in queries:
        query_tokens = tokenize(query_row["query"])
        query_tf = compute_term_frequencies(query_tokens)
        query_vector = {term: tf * idf[term] for term, tf in query_tf.items() if term in idf}
        if not query_vector:
            results.append({"query_id": query_row["query_id"], "query": query_row["query"], "results": []})
            continue

        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        scored: list[tuple[int, float]] = []
        for doc_id, doc_vector in doc_vectors.items():
            doc_norm = doc_norms[doc_id]
            if doc_norm == 0.0:
                continue
            dot = sum(query_vector.get(term, 0.0) * doc_vector.get(term, 0.0) for term in query_vector)
            score = dot / (query_norm * doc_norm) if dot else 0.0
            if score > 0.0:
                scored.append((doc_id, score))

        scored.sort(key=lambda item: (-item[1], item[0]))
        results.append(
            {
                "query_id": query_row["query_id"],
                "query": query_row["query"],
                "results": [
                    {
                        "doc_id": doc_id,
                        "headline": headlines[doc_id],
                        "score": round(score, 12),
                    }
                    for doc_id, score in scored[:top_k]
                ],
            }
        )
    return results


def generate_report(corpus_path: str, queries_path: str, top_k: int) -> dict[str, object]:
    corpus = load_corpus(corpus_path)
    queries = load_queries(queries_path)
    index = build_index(corpus)
    return {
        "corpus": {
            "num_documents": index["num_documents"],
            "vocabulary_size": index["vocabulary_size"],
            "num_postings": index["num_postings"],
        },
        "queries": search_queries(queries, index, top_k),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline TF-IDF archive search.")
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
