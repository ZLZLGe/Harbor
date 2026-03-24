A commissioning shift flagged a short interferometer segment that needs to be standardized before any follow-up search. The raw data is in `/root/data/candidate_segment.csv` with columns `time_s` and `strain`. The samples are uniformly spaced at 8192 Hz.

Build a one-row summary for segment `OBS-CANDIDATE-17` and write it to the CSV path provided in the environment variable `TASK_OUTPUT_FILE`.

Process the strain in this exact order:

1. Take the real FFT of the raw strain, set every frequency bin below 20 Hz to zero, and transform back to the time domain.
2. Downsample the filtered series to 2048 Hz by keeping every 4th sample.
3. Remove 1.5 seconds from the start and 1.5 seconds from the end of the resampled series.
4. Estimate a one-sided PSD from the cropped data using the full-segment periodogram

   `PSD(f) = 2 * dt / N * |rfft(x)|^2`

   where `dt` is the resampled cadence and `N` is the cropped sample count.
5. Compute the arithmetic mean PSD in the inclusive frequency bands 25-40 Hz and 80-120 Hz. Ignore the DC bin in these band statistics.

Write exactly one CSV row with these columns in this order:

```csv
segment_id,final_sample_rate_hz,effective_duration_s,mean_psd_25_40,mean_psd_80_120
```

`effective_duration_s` is the remaining duration after the crop, in seconds.
