# Transfer: Parallel Gzip Log Summarizer

`/root/workspace/` contains a sequential gzip log summarizer. The baseline reads a fixed manifest of compressed log shards, decompresses each `.log.gz` file, parses the lines, and builds an operations report grouped by service and error code.

Write your solution in `/root/workspace/log_summarizer_parallel.py`. Your file must expose these importable functions:

1. `summarize_gzip_logs_parallel(log_dir="/root/workspace/gzip_logs", manifest_path="/root/workspace/log_manifest.json", num_workers=None)`
   - Return a `LogSummaryResult`
   - Use the same `FileDigest` and `LogSummaryResult` structures as `log_summarizer_sequential.py`
   - `result.file_digests` must preserve manifest order
   - `result.num_workers` must report the worker count that was actually used
   - `result.elapsed_time` must be real end-to-end wall-clock time for the summarize step
2. `write_summary_report_parallel(log_dir="/root/workspace/gzip_logs", manifest_path="/root/workspace/log_manifest.json", output_path="/root/workspace/log_summary_report.json", num_workers=None)`
   - Write the final report JSON to `output_path`
   - Return the same report dictionary that was written to disk

Correctness requirements:

- Match the sequential baseline for every `FileDigest` field and for the final report JSON
- Preserve manifest order in `result.file_digests`
- Preserve manifest service order in `report["service_summary"]`
- Keep `report["error_code_summary"]` and `report["hot_files"]` identical to the sequential baseline

Performance requirements:

- The verifier will benchmark the fixed gzip assets already present in `/root/workspace/gzip_logs`
- With `num_workers=2`, the median end-to-end runtime of `write_summary_report_parallel(...)` must achieve at least `1.35x` speedup over the sequential baseline

Constraints:

- Do not modify `log_summarizer_sequential.py`, `build_gzip_log_fixtures.py`, `log_manifest.json`, or the files under `/root/workspace/gzip_logs/`
- Only write your answer to `/root/workspace/log_summarizer_parallel.py`
