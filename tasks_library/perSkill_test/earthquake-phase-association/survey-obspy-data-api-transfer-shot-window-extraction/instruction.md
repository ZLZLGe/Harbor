You are given three inputs:

- `/root/data/survey_line_12_continuous.mseed`: one continuous waveform file for a receiver spread
- `/root/data/receiver_roster.csv`: the receiver rows that are relevant for this task
- `/root/data/shot_schedule.csv`: scheduled shot times for the survey

Your task is to write `/root/shot_window_summary.csv`, one summary row per scheduled shot.

Rules:

1. Read the waveform file and the receiver roster.
2. Only receiver rows whose `enabled` value is `1` are valid for this task.
3. Match waveform traces to the valid receiver roster by the exact tuple `(network, station, location, channel)`.
4. Ignore waveform traces that are not listed as valid receivers.
5. For every shot in `/root/data/shot_schedule.csv`, define a fixed extraction window:
   - `window_start = shot_time - 3.0 seconds`
   - `window_end = shot_time + 7.0 seconds`
6. A trace counts for a shot when its sliced waveform contains at least one sample inside that window.
7. Write exactly one output row per shot with these columns:
   - `shot_id`
   - `line_name`
   - `shot_time`
   - `window_start`
   - `window_end`
   - `trace_count`
   - `station_count`
   - `sample_rates_hz`
   - `total_samples`
8. `trace_count` is the number of counted traces in the window after applying the valid-receiver filter.
9. `station_count` is the number of distinct station codes among those counted traces.
10. `sample_rates_hz` must be the sorted distinct sampling rates of the counted traces, formatted with one decimal place and joined by `|`, for example `40.0|100.0`.
11. `total_samples` is the sum of `trace.stats.npts` across the counted sliced traces.
12. If a shot window contains no counted traces, still include that shot in the output. In that case:
   - `trace_count = 0`
   - `station_count = 0`
   - `sample_rates_hz` is an empty string
   - `total_samples = 0`
13. Sort the final CSV by `shot_time` ascending. If two shots share the same `shot_time`, break ties by `shot_id`.

Formatting requirements:

- All time fields must use ISO format without a timezone suffix, with microsecond precision
- `trace_count` and `station_count` must be integers in the CSV
- `total_samples` must be an integer in the CSV
- Keep the output UTF-8 encoded

The verifier will check:

- the output columns and sort order
- exact window boundaries derived from each `shot_time`
- exact `trace_count`, `station_count`, `sample_rates_hz`, and `total_samples` values
- that zero-hit shots are preserved in the output
