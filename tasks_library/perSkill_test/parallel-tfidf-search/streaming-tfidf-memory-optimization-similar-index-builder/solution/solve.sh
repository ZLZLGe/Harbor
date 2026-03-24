#!/bin/bash
set -euo pipefail

cat <<'PYTHON_EOF' > /root/workspace/streaming_tfidf_solution.py
#!/usr/bin/env python3
"""Streaming TF-IDF solution with reduced peak memory usage."""

from __future__ import annotations

import math
import time
from array import array
from collections import defaultdict

from archive_common import (
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


def _term_frequencies_from_record(record):
    return compute_term_frequencies(tokenize(compose_record_text(record)))


def build_streaming_tfidf_index(corpus_path, batch_size=250):
    del batch_size

    start = time.perf_counter()
    document_frequencies = defaultdict(int)
    titles = []
    num_documents = 0

    for record in iterate_bulletin_jsonl(corpus_path):
        titles.append(record.title)
        term_frequencies = _term_frequencies_from_record(record)
        for term in term_frequencies:
            document_frequencies[term] += 1
        num_documents += 1

    idf = {
        term: math.log(num_documents / df) + 1.0
        for term, df in document_frequencies.items()
    }

    postings = {
        term: PostingList(doc_ids=array("I"), weights=array("d"))
        for term in document_frequencies
    }
    doc_norms = array("d", [0.0]) * num_documents

    for record in iterate_bulletin_jsonl(corpus_path):
        term_frequencies = _term_frequencies_from_record(record)
        norm_squared = 0.0
        for term, tf in term_frequencies.items():
            weight = tf * idf[term]
            postings[term].doc_ids.append(record.doc_id)
            postings[term].weights.append(weight)
            norm_squared += weight * weight
        doc_norms[record.doc_id] = math.sqrt(norm_squared)

    index = StreamingTFIDFIndex(
        num_documents=num_documents,
        vocabulary=tuple(sorted(document_frequencies)),
        document_frequencies=dict(document_frequencies),
        idf=idf,
        postings=postings,
        doc_norms=doc_norms,
        titles=titles,
    )
    elapsed = time.perf_counter() - start
    return StreamingBuildResult(
        index=index,
        elapsed_time=elapsed,
        num_documents=num_documents,
        vocabulary_size=len(index.vocabulary),
    )


def batch_search_streaming(queries, index, top_k=5):
    return search_with_postings(queries, index, top_k=top_k)
PYTHON_EOF

chmod +x /root/workspace/streaming_tfidf_solution.py
