Waveform files are available in `/root/data/`, and `/root/data/phase_reference.csv` provides one P pick and one S pick index for each file.

Create `/root/transfer2_signal_audit.csv` with these columns:
`file_name,pre_rms_scaled,arrival_rms_scaled,coda_rms_scaled,arrival_to_pre_ratio,coda_to_pre_ratio,dominant_channel,s_minus_p_seconds,first_motion`

Rules:
1. Process every row from `phase_reference.csv` and emit exactly one output row per file.
2. Sort rows by `file_name` ascending.
3. Use these sample windows for each file:
   - pre-arrival: `[p_idx - 400, p_idx - 100)`
   - arrival: `[p_idx, s_idx + 1)`
   - coda: `[s_idx + 50, s_idx + 350)`
4. Treat the waveform as multi-component data. For each window, compute RMS over all samples from all available components together.
5. `pre_rms_scaled`, `arrival_rms_scaled`, and `coda_rms_scaled` are the corresponding RMS values multiplied by `1e10` and rounded to six decimal places.
6. `arrival_to_pre_ratio` and `coda_to_pre_ratio` are the unscaled RMS ratios rounded to six decimal places.
7. `dominant_channel` is the component with the largest absolute amplitude inside the arrival window. Break ties by the first component in file order.
8. `s_minus_p_seconds` is `(s_idx - p_idx) * dt`, rounded to three decimal places.
9. `first_motion` is copied from the waveform metadata exactly as stored in the file.
10. Do not read anything from `/tests`.
