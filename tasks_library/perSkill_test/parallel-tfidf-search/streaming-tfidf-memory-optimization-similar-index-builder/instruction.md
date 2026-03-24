# Similar: Streaming TF-IDF Index Builder

In `/root/workspace/`, there is a baseline TF-IDF archive indexer for transit service bulletins. It is exact, but it keeps too many full intermediate structures in memory while building the index.

This task is intended to use the shipped skill in `environment/skills/` that focuses on reducing memory usage.

Write your solution in `/root/workspace/streaming_tfidf_solution.py`.

You must implement these functions:

1. `build_streaming_tfidf_index(corpus_path, batch_size=250)`
2. `batch_search_streaming(queries, index, top_k=5)`

The input corpus is a JSONL file where each line is one bulletin record. Helper code in `/root/workspace/archive_common.py`, `/root/workspace/bulletin_corpus.py`, and `/root/workspace/archive_index_baseline.py` defines the record format, tokenizer, and exact baseline behavior.

Requirements:

- Preserve the baseline ranking and scores for the same corpus and queries.
- Build the index directly from the JSONL corpus path without materializing the whole corpus and all tokenized intermediates at once.
- Return a build result object with `.index`, `.elapsed_time`, `.num_documents`, and `.vocabulary_size`.
- The returned index must expose `.num_documents`, `.document_frequencies`, `.idf`, `.postings`, `.doc_norms`, and `.titles`.
- Each posting list in `.postings` must provide aligned `doc_ids` and `weights` sequences.
- `batch_search_streaming` must return one result list per query, using `SearchHit` objects from `archive_common.py`.

The verifier checks:

- exact agreement with the baseline on fixed and generated corpora
- correct retrieval behavior on the provided bulletin asset
- a substantially lower traced peak memory footprint than the baseline builder on a larger corpus

Do not modify the baseline helper files or the provided corpus assets.
