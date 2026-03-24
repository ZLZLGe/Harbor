# Transfer: Low-RAM Telemetry Window Statistics

In `/root/workspace/`, there is a baseline analyzer for refrigerated-trailer telemetry. It produces exact per-sensor rolling window summaries, but it reads the whole CSV into memory and keeps full per-sensor histories alive.

Write your solution in `/root/workspace/telemetry_window_solution.py`.

You must implement these functions:

1. `compute_window_statistics(csv_path, window_size=12, anomaly_sigma=2.25)`
2. `write_anomaly_summary_json(csv_path, output_path, window_size=12, anomaly_sigma=2.25)`

The input is a CSV file sorted by ascending timestamp, with multiple sensor streams interleaved. Helper code in `/root/workspace/telemetry_common.py`, `/root/workspace/telemetry_baseline.py`, and `/root/workspace/telemetry_factory.py` defines the record format, summary schema, baseline behavior, and synthetic telemetry generator used by the verifier.

Summary rules:

- Evaluate each sensor independently in its own arrival order.
- A complete window contains exactly `window_size` readings for one sensor.
- `mean_of_window_means` is the arithmetic mean of every complete window mean for that sensor.
- `peak_window_stddev` is the maximum population standard deviation among that sensor's complete windows.
- For each complete window, compute an anomaly score as `abs(last_reading - window_mean) / window_stddev`. If `window_stddev` is `0.0`, use an anomaly score of `0.0`.
- A window is anomalous when its anomaly score is greater than or equal to `anomaly_sigma`.
- `first_anomaly_timestamp` is the timestamp of the earliest anomalous window's last reading, or `None` if there is no anomaly.
- Return one `TelemetryWindowSummary` per sensor, sorted by ascending `sensor_id`.

Requirements:

- Preserve the exact summary values and ordering produced by the baseline for the same CSV file.
- Process the CSV directly from `csv_path` without materializing the full parsed file and all per-sensor reading lists at once.
- `compute_window_statistics` must return a list of `TelemetryWindowSummary` objects from `telemetry_common.py`.
- `write_anomaly_summary_json` must write the JSON serialization produced by `summary_to_dict` in `telemetry_common.py`.
- The verifier checks a provided fixture CSV, randomized generated telemetry, and a memory benchmark on a much larger telemetry file.

Do not modify the helper modules or the provided fixture assets.
