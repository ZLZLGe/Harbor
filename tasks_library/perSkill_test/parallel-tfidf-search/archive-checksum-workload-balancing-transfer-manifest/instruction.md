# Transfer: Archive Checksum Manifest Builder

In `/root/workspace/`, there is a sequential checksum manifest builder used for validating outbound archive transfers.

The archive tree mixes many tiny metadata files with a smaller number of very large payloads. A naive split often leaves one worker stuck on the biggest files while the others finish early, so the parallel version needs to stay correct and keep the work more even.

Write your solution in `/root/workspace/checksum_balance_solution.py`. Your code must implement:

1. `build_checksum_manifest_parallel(root_dir, num_workers=None, chunk_size=8)`
   Return a `ParallelManifestResult` whose `manifest` matches the sequential `ChecksumManifest` structure from the workspace.

Requirements:

- Match the sequential manifest exactly for every file entry, including path order, file sizes, SHA-256 digest, and block digest.
- Preserve deterministic ordering even if files finish hashing in a different order internally.
- Reuse the workspace `hash_file` helper for per-file hashing; the verifier may replace that helper with a deterministic stand-in when checking balancing behavior.
- On the verifier's skewed synthetic benchmark with 4 workers, your parallel implementation must achieve at least `1.15x` speedup relative to `build_checksum_manifest_sequential`.
- The verifier will compare your output against the sequential implementation in the workspace.
