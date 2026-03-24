You are given a ground-based differential photometry series for an asteroid at `/root/data/asteroid_ground_photometry.csv` with the columns:

- `time_jd`
- `diff_flux`
- `flux_err`
- `night_id`
- `quality_flag` (`0` means the cadence is usable)

The observations span several nights and include nightly zero-point offsets, slow within-night baseline drift, and cloud-driven outliers. Clean the series so it can be used directly for later rotation analysis.

Requirements:

1. Remove every row with `quality_flag != 0`.
2. Process each `night_id` separately. For that night, compute a centered 21-point running median of `diff_flux`.
3. Define `residual = diff_flux - running_median`.
4. For that night, estimate the robust scatter with:
   `sigma = 1.4826 * median(abs(residual - median(residual)))`
5. Remove points with:
   `abs(residual - median(residual)) > 5 * sigma`
6. Divide the remaining flux values in each night by that night's median flux.
7. Still per night, fit a linear trend
   `a + b * (time_jd - median(time_jd))`
   to the median-normalized flux using ordinary least squares, then divide by that fitted trend.
8. Concatenate the cleaned nights, sort by `time_jd`, and divide the full cleaned series by its overall median so the final median flux is exactly `1.0`.
9. Do not resample or interpolate. Keep only the surviving timestamps from the filtered rows.

Write the result to `/root/asteroid_cleaned.csv` as a CSV file with header:

```text
time_jd,clean_flux
```

Output rules:

- keep rows sorted by `time_jd`
- preserve the original surviving timestamps
- write `time_jd` with at least 8 digits after the decimal point
- round `clean_flux` to 6 decimal places
