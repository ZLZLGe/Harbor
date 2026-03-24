#!/usr/bin/env python3
"""Shared helpers for the streaming TF-IDF archive task."""

from __future__ import annotations

import json
import math
import re
from array import array
from dataclasses import dataclass
from heapq import nsmallest
from pathlib import Path

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "for",
        "from",
        "had",
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
        "there",
        "these",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)
TOKEN_PATTERN = re.compile(r"\b[a-z]{2,}\b")


@dataclass(slots=True)
class BulletinRecord:
    doc_id: int
    line_code: str
    title: str
    summary: str
    body: str
    tags: list[str]


@dataclass(slots=True)
class SearchHit:
    doc_id: int
    score: float
    title: str


@dataclass(slots=True)
class PostingList:
    doc_ids: array
    weights: array


@dataclass(slots=True)
class StreamingTFIDFIndex:
    num_documents: int
    vocabulary: tuple[str, ...]
    document_frequencies: dict[str, int]
    idf: dict[str, float]
    postings: dict[str, PostingList]
    doc_norms: array
    titles: list[str]


@dataclass(slots=True)
class StreamingBuildResult:
    index: StreamingTFIDFIndex
    elapsed_time: float
    num_documents: int
    vocabulary_size: int


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_PATTERN.findall(text.lower())
    return [token for token in tokens if token not in STOP_WORDS]


def compute_term_frequencies(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}

    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1

    total = float(len(tokens))
    return {term: count / total for term, count in counts.items()}


def compose_record_text(record: BulletinRecord) -> str:
    return " ".join(
        [
            record.title,
            record.summary,
            record.body,
            " ".join(record.tags),
            record.line_code,
        ]
    )


def load_bulletin_jsonl(path: str | Path) -> list[BulletinRecord]:
    records: list[BulletinRecord] = []
    for raw in iterate_bulletin_jsonl(path):
        records.append(raw)
    return records


def iterate_bulletin_jsonl(path: str | Path):
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            yield BulletinRecord(
                doc_id=int(payload["doc_id"]),
                line_code=payload["line_code"],
                title=payload["title"],
                summary=payload["summary"],
                body=payload["body"],
                tags=list(payload["tags"]),
            )


def query_to_vector(query: str, idf: dict[str, float]) -> tuple[dict[str, float], float]:
    query_tf = compute_term_frequencies(tokenize(query))
    vector: dict[str, float] = {}
    norm_squared = 0.0
    for term, tf in query_tf.items():
        weight = tf * idf.get(term, 0.0)
        if weight == 0.0:
            continue
        vector[term] = weight
        norm_squared += weight * weight
    return vector, math.sqrt(norm_squared)


def search_with_postings(queries: list[str], index: StreamingTFIDFIndex, top_k: int = 5) -> list[list[SearchHit]]:
    all_results: list[list[SearchHit]] = []
    for query in queries:
        query_vector, query_norm = query_to_vector(query, index.idf)
        if not query_vector or query_norm == 0.0:
            all_results.append([])
            continue

        dot_products: dict[int, float] = {}
        for term, q_weight in query_vector.items():
            posting = index.postings.get(term)
            if posting is None:
                continue
            for doc_id, doc_weight in zip(posting.doc_ids, posting.weights):
                dot_products[doc_id] = dot_products.get(doc_id, 0.0) + (q_weight * doc_weight)

        ranked = []
        for doc_id, dot_product in dot_products.items():
            doc_norm = index.doc_norms[doc_id]
            if doc_norm == 0.0:
                continue
            score = dot_product / (query_norm * doc_norm)
            ranked.append(SearchHit(doc_id=doc_id, score=score, title=index.titles[doc_id]))

        ranked.sort(key=lambda item: (-item.score, item.doc_id))
        all_results.append(ranked[:top_k])
    return all_results


def top_doc_ids(results: list[SearchHit]) -> list[int]:
    return [item.doc_id for item in results]


def take_best_ids(results: list[list[SearchHit]], limit: int = 3) -> list[list[int]]:
    return [top_doc_ids(row[:limit]) for row in results]
