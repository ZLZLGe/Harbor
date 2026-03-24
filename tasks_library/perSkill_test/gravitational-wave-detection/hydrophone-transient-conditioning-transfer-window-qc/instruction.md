A seabed hydrophone deployment produced one continuous pressure record that now needs window-level quality control before a transient retrieval pass. The full pressure series is stored in `/root/data/hydrophone_pressure.npy`, and `/root/data/window_manifest.json` contains the raw sample rate, fixed window boundaries, and the maximum allowed low-frequency noise ratio.

Build `/root/hydrophone_window_quality.csv` with one row per window in the manifest.

Process each window in this exact order:

1. Slice the raw pressure series from the continuous record using the manifest interval `[start_time_s, end_time_s)`.
2. Take the real FFT of that raw window, set every frequency bin below 25 Hz to zero, and transform back to the time domain.
3. Downsample the filtered window to 600 Hz by keeping every `raw_sample_rate_hz / 600` sample. The manifest only uses integer multiples of 600 Hz.
4. Remove 0.5 seconds from the start and 0.5 seconds from the end of the resampled window.
5. Estimate a one-sided PSD with Welch averaging using 1.0-second Hann windows and 50% overlap. For each chunk `x`, compute

   `PSD_chunk(f) = 2 * dt / sum(w^2) * |rfft(w * x)|^2`

   where `dt` is the 600 Hz cadence and `w` is the Hann window. Average the chunk PSDs frequency bin by frequency bin.
6. Compute the arithmetic mean PSD in the inclusive frequency bands 25-60 Hz and 120-240 Hz. Ignore the DC bin in these band statistics.
7. Define `low_frequency_noise_ratio = mean_psd_25_60 / mean_psd_120_240`.
8. Read `max_low_frequency_noise_ratio` from the manifest. Set `search_ready` to `READY` if the ratio is less than or equal to that threshold; otherwise set it to `HOLD`.

Write the CSV with these columns in this exact order:

```csv
window_id,start_time_s,end_time_s,conditioned_sample_rate_hz,usable_duration_s,mean_psd_25_60,mean_psd_120_240,low_frequency_noise_ratio,search_ready
```

Additional requirements:

- `conditioned_sample_rate_hz` must be `600`.
- `usable_duration_s` is the duration after the edge crop.
- Output one row for every window listed in the manifest.
- Sort the file by `start_time_s` ascending before writing it.
