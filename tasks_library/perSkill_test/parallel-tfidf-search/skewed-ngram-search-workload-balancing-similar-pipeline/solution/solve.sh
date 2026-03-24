#!/bin/bash
set -euo pipefail

TASK_WORKSPACE="${TASK_WORKSPACE:-/root/workspace}"

cat > "${TASK_WORKSPACE}/ngram_parallel_solution.py" <<'PYTHON_EOF'
#!/usr/bin/env python3
"""
Reference parallel implementation for the skewed n-gram search task.
"""

from __future__ import annotations

import math
import multiprocessing as mp
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ngram_support_corpus import SupportDocument
from sequential_ngram import NGramIndex, SearchResult, compute_normalized_frequencies, extract_char_ngrams

SEARCH_INDEX = None
SEARCH_TOP_K = 10
SEARCH_DOC_TITLES = {}


def _balanced_partitions(items, weights, bucket_count):
    bucket_count = max(1, min(bucket_count, len(items) or 1))
    buckets = [[] for _ in range(bucket_count)]
    costs = [0] * bucket_count
    order = sorted(range(len(items)), key=lambda idx: weights[idx], reverse=True)
    for idx in order:
        target = min(range(bucket_count), key=lambda bucket_idx: costs[bucket_idx])
        buckets[target].append(items[idx])
        costs[target] += weights[idx]
    return [bucket for bucket in buckets if bucket]


def _create_pool(processes, initializer=None, initargs=()):
    try:
        return mp.Pool(processes=processes, initializer=initializer, initargs=initargs)
    except PermissionError:
        return _ThreadPoolAdapter(processes, initializer=initializer, initargs=initargs)


class _ThreadPoolAdapter:
    def __init__(self, processes, initializer=None, initargs=()):
        self._executor = ThreadPoolExecutor(max_workers=processes, initializer=initializer, initargs=initargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._executor.shutdown(wait=True)
        return False

    def map(self, func, iterable, chunksize=1):
        return list(self._executor.map(func, iterable))


def _process_document_batch(args):
    documents, n = args
    doc_term_freqs = {}
    doc_terms = {}
    vocabulary = set()
    doc_lengths = {}

    for doc in documents:
        text = f"{doc.title}\n{doc.content}"
        grams = extract_char_ngrams(text, n=n)
        tf = compute_normalized_frequencies(grams)
        doc_term_freqs[doc.doc_id] = tf
        terms = set(tf)
        doc_terms[doc.doc_id] = terms
        vocabulary.update(terms)
        doc_lengths[doc.doc_id] = doc.char_length

    return doc_term_freqs, doc_terms, vocabulary, doc_lengths


def _build_partial_vectors(args):
    doc_items, idf = args
    partial_inverted = defaultdict(list)
    doc_vectors = {}
    doc_norms = {}

    for doc_id, tf in doc_items:
        vector = {}
        norm_sq = 0.0
        for gram, freq in tf.items():
            weight = freq * idf[gram]
            vector[gram] = weight
            norm_sq += weight * weight
            partial_inverted[gram].append((doc_id, weight))
        doc_vectors[doc_id] = vector
        doc_norms[doc_id] = math.sqrt(norm_sq)

    return dict(partial_inverted), doc_vectors, doc_norms


def _init_search_pool(index, top_k, doc_titles):
    global SEARCH_INDEX, SEARCH_TOP_K, SEARCH_DOC_TITLES
    SEARCH_INDEX = index
    SEARCH_TOP_K = top_k
    SEARCH_DOC_TITLES = doc_titles


def _score_query(query, index, top_k):
    query_grams = extract_char_ngrams(query, n=index.n)
    if not query_grams:
        return []

    query_tf = compute_normalized_frequencies(query_grams)
    query_vector = {}
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
    candidate_docs = set()
    for gram in query_vector:
        for doc_id, _score in index.inverted_index.get(gram, []):
            candidate_docs.add(doc_id)

    scored = []
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


def _search_query_batch(batch):
    output = []
    for query_idx, query in batch:
        rows = []
        for doc_id, score in _score_query(query, SEARCH_INDEX, SEARCH_TOP_K):
            rows.append((doc_id, score, SEARCH_DOC_TITLES.get(doc_id, f"Document {doc_id}")))
        output.append((query_idx, rows))
    return output


@dataclass
class ParallelNGramIndexingResult:
    index: NGramIndex
    elapsed_time: float
    num_documents: int
    vocabulary_size: int
    num_workers: int
    strategy: str


def build_ngram_index_parallel(documents, n=3, num_workers=None, chunk_size=24):
    if num_workers is None:
        num_workers = mp.cpu_count()
    num_workers = max(1, min(num_workers, len(documents) or 1))

    start_time = time.perf_counter()
    weights = [max(doc.char_length, 1) for doc in documents]
    target_from_chunk = max(1, math.ceil(len(documents) / max(chunk_size, 1)))
    base_partitions = max(num_workers * 2, target_from_chunk)
    batches = _balanced_partitions(documents, weights, min(base_partitions, len(documents) or 1))

    with _create_pool(processes=num_workers) as pool:
        processed = pool.map(_process_document_batch, [(batch, n) for batch in batches], chunksize=1)

    doc_term_freqs = {}
    doc_terms = {}
    vocabulary = set()
    doc_lengths = {}
    for batch_tf, batch_terms, batch_vocab, batch_lengths in processed:
        doc_term_freqs.update(batch_tf)
        doc_terms.update(batch_terms)
        vocabulary.update(batch_vocab)
        doc_lengths.update(batch_lengths)

    index = NGramIndex(num_documents=len(documents), n=n)
    index.vocabulary = vocabulary
    for gram in vocabulary:
        index.document_frequencies[gram] = sum(1 for terms in doc_terms.values() if gram in terms)
        index.idf[gram] = math.log(len(documents) / index.document_frequencies[gram]) + 1.0

    doc_items = list(doc_term_freqs.items())
    vector_weights = [max(doc_lengths.get(doc_id, len(tf) * n), 1) for doc_id, tf in doc_items]
    vector_batches = _balanced_partitions(doc_items, vector_weights, min(base_partitions, len(doc_items) or 1))

    with _create_pool(processes=num_workers) as pool:
        partials = pool.map(_build_partial_vectors, [(batch, index.idf) for batch in vector_batches], chunksize=1)

    for partial_inverted, partial_vectors, partial_norms in partials:
        for gram, postings in partial_inverted.items():
            index.inverted_index.setdefault(gram, []).extend(postings)
        index.doc_vectors.update(partial_vectors)
        index.doc_norms.update(partial_norms)

    for postings in index.inverted_index.values():
        postings.sort(key=lambda item: (-item[1], item[0]))

    elapsed_time = time.perf_counter() - start_time
    return ParallelNGramIndexingResult(
        index=index,
        elapsed_time=elapsed_time,
        num_documents=len(documents),
        vocabulary_size=len(vocabulary),
        num_workers=num_workers,
        strategy="cost-balanced-batches",
    )


def batch_search_parallel(queries, index, top_k=10, num_workers=None, documents=None):
    if num_workers is None:
        num_workers = mp.cpu_count()
    num_workers = max(1, min(num_workers, len(queries) or 1))

    start_time = time.perf_counter()
    doc_titles = {doc.doc_id: doc.title for doc in documents} if documents else {}
    items = list(enumerate(queries))
    weights = [max(len(query), 1) for query in queries]
    batches = _balanced_partitions(items, weights, min(num_workers * 4, len(items) or 1))

    with _create_pool(
        processes=num_workers,
        initializer=_init_search_pool,
        initargs=(index, top_k, doc_titles),
    ) as pool:
        partial_results = pool.map(_search_query_batch, batches, chunksize=1)

    ordered = [[] for _ in queries]
    for batch in partial_results:
        for query_idx, rows in batch:
            ordered[query_idx] = [SearchResult(doc_id=doc_id, score=score, title=title) for doc_id, score, title in rows]

    elapsed_time = time.perf_counter() - start_time
    return ordered, elapsed_time
PYTHON_EOF

chmod +x "${TASK_WORKSPACE}/ngram_parallel_solution.py"
