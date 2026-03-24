You are given a ground-based quasar monitoring light curve at `/root/data/quasar_monitoring.csv` with the columns:

- `mjd`
- `relative_flux`
- `flux_err`
- `season_id`
- `quality_flag` (`0` means the exposure is usable)

The monitoring spans several observing seasons. Each season has its own zero-point offset, there are a few isolated bad exposures, and the quasar also shows slow baseline wander within a season. Clean the light curve and report the RMS of the residual variability after season-by-season normalization and detrending.

Requirements:

1. Remove every row with `quality_flag != 0`.
2. Process each `season_id` separately, keeping rows in time order.
3. For each season, compute a centered 5-point running median of `relative_flux`.
4. Define `residual = relative_flux - running_median`.
5. For that season, estimate the robust scatter with:
   `sigma = 1.4826 * median(abs(residual - median(residual)))`
6. Remove points with:
   `abs(residual - median(residual)) > 4.5 * sigma`
7. For the surviving points in that season, divide `relative_flux` by that season's median surviving flux.
8. On the season-normalized flux, compute a centered 9-point running median and use it as the seasonal trend.
9. Define the detrended residual series for that season as:
   `season_residual = season_normalized_flux / seasonal_trend - 1.0`
10. Concatenate all season residuals and compute:
    `RMS = sqrt(mean(season_residual^2))`
11. Do not interpolate or resample. Use only the surviving observed cadences.

Write the result to `/root/quasar_rms.txt` as:

- a single numeric value
- rounded to 6 decimal places

Example format:

```text
0.006779
```
