# Similar: Skewed N-Gram Search Pipeline

In `/root/workspace/`, there is a sequential character n-gram search pipeline for a support-ticket archive.

The archive mixes many short ticket summaries with a smaller number of very long chat transcripts and postmortems. A naive parallel split tends to leave one worker stuck on the longest items, so the implementation needs to stay correct while handling that skew more evenly.

Write your solution in `/root/workspace/ngram_parallel_solution.py`. Your code must implement these functions:

1. `build_ngram_index_parallel(documents, n=3, num_workers=None, chunk_size=24)`
   Return a `ParallelNGramIndexingResult` whose `index` matches the sequential `NGramIndex` structure.

2. `batch_search_parallel(queries, index, top_k=10, num_workers=None, documents=None)`
   Return `(List[List[SearchResult]], elapsed_time)`.

Requirements:

- Keep the parallel results identical to the sequential baseline for indexing and ranked search results.
- Preserve deterministic ordering for tied search scores.
- Improve throughput on the provided skewed corpus with 4 workers for both index building and batch search.
- The verifier will compare your output against the sequential implementation in the workspace.
