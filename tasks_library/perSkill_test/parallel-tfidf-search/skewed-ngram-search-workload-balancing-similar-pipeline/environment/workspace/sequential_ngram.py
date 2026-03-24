#!/usr/bin/env python3
"""
Sequential character n-gram indexing and fuzzy search baseline.
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ngram_support_corpus import SupportDocument, generate_query_batch, generate_support_corpus

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
SPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    lowered = text.lower()
    compact = NORMALIZE_PATTERN.sub(" ", lowered)
    return SPACE_PATTERN.sub(" ", compact).strip()


def extract_char_ngrams(text: str, n: int = 3) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    padded = f" {normalized} "
    if len(padded) <= n:
        return [padded]
    return [padded[idx : idx + n] for idx in range(len(padded) - n + 1)]


def compute_normalized_frequencies(ngrams: list[str]) -> dict[str, float]:
    if not ngrams:
        return {}
    counts = Counter(ngrams)
    total = float(len(ngrams))
    return {gram: count / total for gram, count in counts.items()}


@dataclass
class NGramIndex:
    num_documents: int = 0
    n: int = 3
    vocabulary: set[str] = field(default_factory=set)
    document_frequencies: dict[str, int] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)
    inverted_index: dict[str, list[tuple[int, float]]] = field(default_factory=dict)
    doc_vectors: dict[int, dict[str, float]] = field(default_factory=dict)
    doc_norms: dict[int, float] = field(default_factory=dict)


@dataclass
class SearchResult:
    doc_id: int
    score: float
    title: str = ""


@dataclass
class IndexingResult:
    index: NGramIndex
    elapsed_time: float
    num_documents: int
    vocabulary_size: int


def build_ngram_index_sequential(documents: list[SupportDocument], n: int = 3) -> IndexingResult:
    start_time = time.perf_counter()
    index = NGramIndex(num_documents=len(documents), n=n)
    doc_tf: dict[int, dict[str, float]] = {}
    doc_terms: dict[int, set[str]] = {}

    for doc in documents:
        text = f"{doc.title}\n{doc.content}"
        grams = extract_char_ngrams(text, n=n)
        tf = compute_normalized_frequencies(grams)
        doc_tf[doc.doc_id] = tf
        term_set = set(tf)
        doc_terms[doc.doc_id] = term_set
        index.vocabulary.update(term_set)

    for gram in index.vocabulary:
        index.document_frequencies[gram] = sum(1 for terms in doc_terms.values() if gram in terms)

    total_docs = len(documents)
    for gram, df in index.document_frequencies.items():
        index.idf[gram] = math.log(total_docs / df) + 1.0

    for gram in index.vocabulary:
        postings: list[tuple[int, float]] = []
        for doc_id, tf in doc_tf.items():
            if gram in tf:
                score = tf[gram] * index.idf[gram]
                postings.append((doc_id, score))
        postings.sort(key=lambda item: (-item[1], item[0]))
        index.inverted_index[gram] = postings

    for doc_id, tf in doc_tf.items():
        vector: dict[str, float] = {}
        norm_sq = 0.0
        for gram, freq in tf.items():
            weight = freq * index.idf[gram]
            vector[gram] = weight
            norm_sq += weight * weight
        index.doc_vectors[doc_id] = vector
        index.doc_norms[doc_id] = math.sqrt(norm_sq)

    elapsed = time.perf_counter() - start_time
    return IndexingResult(index=index, elapsed_time=elapsed, num_documents=len(documents), vocabulary_size=len(index.vocabulary))


def _score_query(query: str, index: NGramIndex, top_k: int) -> list[tuple[int, float]]:
    query_grams = extract_char_ngrams(query, n=index.n)
    if not query_grams:
        return []

    query_tf = compute_normalized_frequencies(query_grams)
    query_vector: dict[str, float] = {}
    query_norm_sq = 0.0
    for gram, freq in query_tf.items():
        if gram not in index.idf:
            continue
        weight = freq * index.idf[gram]
        query_vector[gram] = weight
        query_norm_sq += weight * weight

    if not query_vector:
        return []

    query_norm = math.sqrt(query_norm_sq)
    candidate_docs: set[int] = set()
    for gram in query_vector:
        for doc_id, _score in index.inverted_index.get(gram, []):
            candidate_docs.add(doc_id)

    scored: list[tuple[int, float]] = []
    for doc_id in candidate_docs:
        doc_vector = index.doc_vectors.get(doc_id, {})
        doc_norm = index.doc_norms.get(doc_id, 0.0)
        if doc_norm == 0.0:
            continue
        dot_product = 0.0
        for gram, weight in query_vector.items():
            dot_product += weight * doc_vector.get(gram, 0.0)
        similarity = dot_product / (query_norm * doc_norm)
        if similarity > 0.0:
            scored.append((doc_id, similarity))

    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:top_k]


def search_sequential(
    query: str,
    index: NGramIndex,
    top_k: int = 10,
    documents: list[SupportDocument] | None = None,
) -> list[SearchResult]:
    doc_titles = {doc.doc_id: doc.title for doc in documents} if documents else {}
    return [
        SearchResult(doc_id=doc_id, score=score, title=doc_titles.get(doc_id, f"Document {doc_id}"))
        for doc_id, score in _score_query(query, index, top_k)
    ]


def batch_search_sequential(
    queries: list[str],
    index: NGramIndex,
    top_k: int = 10,
    documents: list[SupportDocument] | None = None,
) -> list[list[SearchResult]]:
    return [search_sequential(query, index, top_k=top_k, documents=documents) for query in queries]


if __name__ == "__main__":
    documents = generate_support_corpus(200, seed=42)
    result = build_ngram_index_sequential(documents)
    queries = generate_query_batch(documents, 5, seed=99)
    print(f"Indexed {result.num_documents} documents in {result.elapsed_time:.3f}s")
    for query in queries:
        hits = search_sequential(query, result.index, top_k=3, documents=documents)
        print(query)
        for hit in hits:
            print(f"  {hit.doc_id}: {hit.score:.4f} {hit.title}")
