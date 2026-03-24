You are given strong-motion acceleration records at `/root/data/accelerometer_records.csv` and station metadata at `/root/data/stations.csv`.

This task is about low-latency alert screening during one large earthquake, not offline catalog building.

Data layout:
- `accelerometer_records.csv` contains one uniformly sampled time series table. The `time` column is the sample timestamp in ISO format without timezone. Every other column is one station trace listed in `stations.csv`.
- `stations.csv` provides station-level metadata, including the `trace_column` name for each station, the sample rate, units, and location fields.

Your goal is to choose a trigger approach that is appropriate for fast, explainable screening of obvious strong-motion onsets, then report when each station should open its first alert window.

Write your result to `/root/alert_windows.csv`.

The output must contain at least these columns:
- `station`
- `window_start`
- `trigger_score`

Requirements:
1. Output exactly one row for each station listed in `stations.csv`.
2. `window_start` must be in ISO format without timezone.
3. `trigger_score` must be numeric.
4. Rows must be sorted by `window_start`.
5. The reported time should be the earliest usable alert-window start for that station once strong shaking begins, not a later refined phase pick.

You may include extra columns if helpful, but the required columns above must be present.
