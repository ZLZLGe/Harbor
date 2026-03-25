Waveform files are available in `/root/data/`. Analyst requests for waveform excerpts are listed in `/root/data/window_requests.json`.

Create `/root/transfer3_window_manifest.json` with this structure:
1. A top-level integer field `requests_processed`
2. A top-level array field `windows`

For every request, add one object to `windows` with these fields:
`file_name`, `window_start_utc`, `window_end_utc`, `start_idx`, `end_idx`, `sample_count`, `channel_codes`, `peak_channel`, `peak_offset_samples`, `window_duration_seconds`, `window_peak_abs_scaled`, `window_mean_abs_scaled`

Rules:
1. Preserve request order.
2. Use the waveform start time and sample rate from each file to convert `window_start_utc` and `window_end_utc` into sample indices.
3. Compute `start_idx` and `end_idx` by rounding to the nearest sample.
4. Treat `start_idx` as inclusive and `end_idx` as exclusive, then clip both values to the valid trace bounds.
5. If clipping would make `end_idx <= start_idx`, force `end_idx = start_idx + 1` unless the trace is empty.
6. `sample_count` is `end_idx - start_idx`.
7. `peak_channel` is the component with the largest absolute amplitude inside the requested window. Break ties by the first component in file order.
8. `peak_offset_samples` is the zero-based offset of the first maximum absolute amplitude within `peak_channel` inside the extracted window.
9. `window_duration_seconds` is `sample_count / sampling_rate`, rounded to three decimal places.
10. `window_peak_abs_scaled` and `window_mean_abs_scaled` come from `peak_channel`, multiplied by `1e10` and rounded to six decimal places.
11. Do not read anything from `/tests`.
