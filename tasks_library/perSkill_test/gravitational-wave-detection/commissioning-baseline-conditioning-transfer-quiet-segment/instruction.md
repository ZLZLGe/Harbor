An interferometer commissioning run produced several raw quiet-time segments that need to be put on the same footing before choosing a baseline. The strain arrays are stored in `/root/data/commissioning_segments.npz`, and `/root/data/segment_manifest.csv` lists each segment ID with its original sample rate.

Build `/root/commissioning_noise_baseline.csv` with one row per segment.

Process every segment in this exact order:

1. Load the raw strain array for the segment.
2. Take the real FFT of the raw strain, set every frequency bin below 20 Hz to zero, and transform back to the time domain.
3. Downsample the filtered series to 1024 Hz by keeping every `raw_sample_rate_hz / 1024` sample. The manifest only contains integer multiples of 1024 Hz.
4. Remove 2.0 seconds from the start and 2.0 seconds from the end of the resampled series.
5. Estimate a one-sided PSD with Welch averaging using 2.0-second Hann windows and 50% overlap. For each windowed chunk `x`, compute

   `PSD_chunk(f) = 2 * dt / sum(w^2) * |rfft(w * x)|^2`

   where `dt` is the 1024 Hz cadence and `w` is the Hann window. Average the chunk PSDs frequency bin by frequency bin.
6. Compute the arithmetic mean PSD in the inclusive frequency bands 20-200 Hz and 200-500 Hz. Ignore the DC bin in these band statistics.
7. Define `baseline_score = 0.5 * (mean_psd_20_200 + mean_psd_200_500)`.
8. Rank segments from quietest to loudest using ascending `baseline_score`. Break ties by `segment_id` in ascending order.

Write the CSV with these columns in this exact order:

```csv
segment_id,raw_sample_rate_hz,conditioned_sample_rate_hz,usable_duration_s,mean_psd_20_200,mean_psd_200_500,baseline_score,quiet_rank
```

Additional requirements:

- `conditioned_sample_rate_hz` must be `1024`.
- `usable_duration_s` is the duration after the edge crop.
- Output one row for every segment listed in the manifest.
- Sort the file by `quiet_rank` ascending before writing it.
