# Transfer: Parallel Photo Deduplication via Perceptual Hashing

In `/root/workspace/`, there is a sequential photo dedupe tool for deterministic grayscale `.pgm` images. It scans an album directory, computes a perceptual hash for every photo, and groups likely duplicates into clusters using Hamming distance.

You need to parallelize the expensive hash-building stage while preserving the exact record order, hash values, and duplicate clusters produced by the sequential baseline.

Write your solution in `/root/workspace/parallel_photo_dedupe.py` and implement these functions:

1. `build_photo_index_parallel(album_dir, hash_size=8, num_workers=None, chunk_size=12)`
   - Return a `ParallelHashBuildResult`
   - Preserve the same `PhotoHashIndex` and `PhotoHashRecord` structure used by the provided baseline files
   - Preserve the sorted album traversal order from `discover_photo_paths`

2. `run_photo_dedupe_parallel(album_dir, hash_size=8, max_hamming_distance=18, num_workers=None, chunk_size=12)`
   - Return the same report dictionary shape as the sequential pipeline
   - Duplicate clusters, member ordering, and summary counts must exactly match the sequential baseline

Requirements:

- Use multiple worker processes for the CPU-bound hash computation
- Split independent photo batches explicitly instead of hashing the entire album in one worker
- Keep the sequential clustering semantics unchanged
- Stay compatible with the provided helper modules and deterministic album fixtures

Performance target with 4 workers on the generated verification album:

- Parallel index building should achieve at least `1.35x` speedup over the sequential baseline

Files already provided in `/root/workspace/`:

- `photo_fixture.py`: deterministic album generation, `.pgm` helpers, and album discovery
- `album_blueprints.json`: a small blueprint used by the correctness tests
- `sequential_photo_dedupe.py`: sequential baseline implementation

Your implementation must stay compatible with those files.
