# Transfer: Vectorized Sensor Window Scoring

`/root/workspace/` contains a sequential sensor-window scoring pipeline. The baseline loads a fixed batch of numeric windows from `sensor_windows.npz`, applies rolling statistics to each window, computes anomaly metrics, and can write a CSV report.

Write your solution in `/root/workspace/vectorized_scores.py`. Your file must expose these importable functions:

1. `score_sensor_windows_vectorized(windows_path="/root/workspace/sensor_windows.npz", manifest_path="/root/workspace/window_manifest.json", chunk_size=None)`
   - Return a `ScoreBatchResult`
   - Use the same `WindowScore` and `ScoreBatchResult` structures as `sensor_scoring_sequential.py`
   - `result.scores` must preserve the input window order
   - `result.elapsed_time` must be the real end-to-end wall-clock time for the scoring step
2. `write_window_score_report(windows_path="/root/workspace/sensor_windows.npz", manifest_path="/root/workspace/window_manifest.json", output_path="/root/workspace/window_scores_report.csv", chunk_size=None)`
   - Write the per-window report to `output_path` as CSV
   - Return the same summary dictionary produced by the sequential baseline

Correctness requirements:

- Match the sequential baseline for every `WindowScore` field; floating-point fields may differ by at most `1e-6`
- Match the sequential baseline for `result.summary`
- Write the same CSV header and rows as the sequential baseline
- Preserve window order in both `result.scores` and the CSV output

Performance requirements:

- The verifier will use the fixed benchmark assets already present in `/root/workspace/`
- Using the default benchmark inputs, the median runtime of `score_sensor_windows_vectorized(...)` must achieve at least `3.00x` speedup over the sequential baseline

Constraints:

- Do not modify `sensor_scoring_sequential.py`, `build_sensor_assets.py`, `sensor_windows.npz`, or `window_manifest.json`
- Only write your answer to `/root/workspace/vectorized_scores.py`
