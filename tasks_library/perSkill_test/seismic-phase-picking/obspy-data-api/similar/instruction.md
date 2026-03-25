Eight bundled waveform traces are available in `/root/data/`, together with a reference table at `/root/data/phase_reference.csv`.

Create `/root/similar_phase_timeline.csv` with these columns:
`file_name,network,station,vertical_channel,p_arrival_utc,s_arrival_utc,s_minus_p_seconds,vertical_peak_idx,vertical_peak_abs_scaled`

Rules:
1. Process every row from `phase_reference.csv` and emit exactly one output row per file.
2. Sort rows by `file_name` ascending.
3. Use the waveform header metadata in each `.npz` file to determine the trace start time, sample rate, network, station, and channel codes.
4. Treat the vertical component as the first channel whose code ends with `Z`. If multiple channels qualify, use the first one.
5. Convert `p_idx` and `s_idx` into UTC timestamps from the trace start time. Format both timestamps as `YYYY-MM-DDTHH:MM:SS.ffffffZ`.
6. `s_minus_p_seconds` is `(s_idx - p_idx) * dt`, rounded to three decimal places.
7. Compute `vertical_peak_idx` from the inclusive sample window between `p_idx` and `s_idx` on the vertical component. Use the first index that reaches the maximum absolute amplitude.
8. `vertical_peak_abs_scaled` is that maximum absolute amplitude multiplied by `1e10` and rounded to six decimal places.
9. Do not read anything from `/tests`.
