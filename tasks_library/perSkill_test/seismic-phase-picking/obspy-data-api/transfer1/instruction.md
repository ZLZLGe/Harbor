You are preparing an intake manifest for the waveform files bundled in `/root/data/`.

Create `/root/transfer1_waveform_catalog.json` with this structure:
1. A top-level object named `summary`
2. A top-level array named `files`

Rules for each entry in `files`:
1. Include one entry for every `.npz` file in `/root/data/`, sorted by `file_name`.
2. Each entry must contain:
   `file_name`, `network`, `station`, `location_code`, `channel_codes`, `trace_count`, `sample_rate_hz`, `duration_seconds`, `start_utc`, `end_utc`, `event_time_utc`, `distance_km`, `event_magnitude`, `peak_component`, `peak_abs_scaled`, `mean_snr`
3. `channel_codes` must preserve the waveform component order from the file metadata.
4. `duration_seconds` is the trace end time minus the trace start time, rounded to three decimal places.
5. `start_utc`, `end_utc`, and `event_time_utc` must use `YYYY-MM-DDTHH:MM:SS.ffffffZ`.
6. `peak_component` is the component with the largest absolute amplitude across the full waveform. Break ties by the first component in file order.
7. `peak_abs_scaled` is that amplitude multiplied by `1e10` and rounded to six decimal places.
8. `mean_snr` is the arithmetic mean of the file's SNR values, rounded to four decimal places.

Rules for `summary`:
1. Include `total_files`, `network_counts`, `earliest_start_utc`, `latest_end_utc`, `mean_duration_seconds`, and `max_distance_km`.
2. `network_counts` must be a JSON object whose keys are sorted alphabetically.
3. `mean_duration_seconds` is the average of the per-file durations, rounded to three decimal places.
4. `max_distance_km` is rounded to one decimal place.

Do not read anything from `/tests`.
