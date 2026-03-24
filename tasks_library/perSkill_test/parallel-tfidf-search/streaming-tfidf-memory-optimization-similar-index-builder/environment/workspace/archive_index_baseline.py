#!/usr/bin/env python3
"""Exact but memory-hungry baseline TF-IDF archive indexer."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from archive_common import (
    BulletinRecord,
    PostingList,
    SearchHit,
    StreamingBuildResult,
    StreamingTFIDFIndex,
    compose_record_text,
    compute_term_frequencies,
    iterate_bulletin_jsonl,
    search_with_postings,
    tokenize,
)


@dataclass
class BaselineTFIDFIndex:
    num_documents: int = 0
    vocabulary: set[str] = field(default_factory=set)
    document_frequencies: dict[str, int] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)
    postings: dict[str, list[tuple[int, float]]] = field(default_factory=dict)
    doc_vectors: dict[int, dict[str, float]] = field(default_factory=dict)
    doc_norms: dict[int, float] = field(default_factory=dict)
    titles: list[str] = field(default_factory=list)


@dataclass
class BaselineBuildResult:
    index: BaselineTFIDFIndex
    elapsed_time: float
    num_documents: int
    vocabulary_size: int


def load_records(corpus_path: str) -> list[BulletinRecord]:
    return list(iterate_bulletin_jsonl(corpus_path))


def build_archive_index_baseline(corpus_path: str) -> BaselineBuildResult:
    start = time.perf_counter()
    records = load_records(corpus_path)

    index = BaselineTFIDFIndex(num_documents=len(records))
    index.titles = [record.title for record in records]

    doc_tokens: dict[int, list[str]] = {}
    doc_term_freqs: dict[int, dict[str, float]] = {}
    doc_terms: dict[int, set[str]] = {}

    for record in records:
        tokens = tokenize(compose_record_text(record))
        doc_tokens[record.doc_id] = tokens
        tf = compute_term_frequencies(tokens)
        doc_term_freqs[record.doc_id] = tf
        doc_terms[record.doc_id] = set(tf)
        index.vocabulary.update(tf)

    for term in index.vocabulary:
        index.document_frequencies[term] = sum(1 for doc_id in doc_terms if term in doc_terms[doc_id])

    for term, df in index.document_frequencies.items():
        index.idf[term] = math.log(index.num_documents / df) + 1.0

    for term in index.vocabulary:
        posting_list: list[tuple[int, float]] = []
        for doc_id, tf_map in doc_term_freqs.items():
            weight = tf_map.get(term)
            if weight is None:
                continue
            posting_list.append((doc_id, weight * index.idf[term]))
        posting_list.sort(key=lambda item: (-item[1], item[0]))
        index.postings[term] = posting_list

    for doc_id, tf_map in doc_term_freqs.items():
        doc_vector: dict[str, float] = {}
        norm_squared = 0.0
        for term, tf in tf_map.items():
            weight = tf * index.idf[term]
            doc_vector[term] = weight
            norm_squared += weight * weight
        index.doc_vectors[doc_id] = doc_vector
        index.doc_norms[doc_id] = math.sqrt(norm_squared)

    elapsed = time.perf_counter() - start
    return BaselineBuildResult(
        index=index,
        elapsed_time=elapsed,
        num_documents=index.num_documents,
        vocabulary_size=len(index.vocabulary),
    )


def batch_search_baseline(queries: list[str], index: BaselineTFIDFIndex, top_k: int = 5) -> list[list[SearchHit]]:
    compact = StreamingTFIDFIndex(
        num_documents=index.num_documents,
        vocabulary=tuple(sorted(index.vocabulary)),
        document_frequencies=dict(index.document_frequencies),
        idf=dict(index.idf),
        postings={
            term: PostingList(
                doc_ids=__import__("array").array("I", (doc_id for doc_id, _ in rows)),
                weights=__import__("array").array("d", (weight for _, weight in rows)),
            )
            for term, rows in index.postings.items()
        },
        doc_norms=__import__("array").array(
            "d",
            [index.doc_norms.get(doc_id, 0.0) for doc_id in range(index.num_documents)],
        ),
        titles=list(index.titles),
    )
    return search_with_postings(queries, compact, top_k=top_k)
