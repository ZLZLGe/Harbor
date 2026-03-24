You are given a TESS-style light curve at `/root/data/known_transit_lc.csv` with the columns:

- `time_btjd`
- `normalized_flux`
- `quality_flag` (`0` means usable cadence)
- `flux_err`

The light curve contains low-frequency stellar variability, injected outliers, and non-zero quality flags. A known transit ephemeris is provided at `/root/data/known_ephemeris.csv` with:

- `period_days`
- `reference_mid_transit_btjd`
- `transit_duration_hours`

Measure the transit depth after cleaning and detrending the light curve.

Requirements:

1. Filter out cadences with non-zero quality flags.
2. Remove obvious flux outliers.
3. Remove the low-frequency stellar trend while preserving the short transit shape.
4. Use the provided ephemeris to evaluate only complete predicted transits.
   A transit is complete only if the full window from `mid_transit - 3 * duration` to `mid_transit + 3 * duration` lies inside the observed time span.
5. On the detrended light curve, define:
   - in-transit points: `|time - mid_transit| <= duration / 2`
   - local comparison points: `duration <= |time - mid_transit| <= 3 * duration`
6. Compute the transit depth as:
   `median(local comparison flux) - median(in-transit flux)`
   using all complete predicted transits together.

Write the result to `/root/transit_depth.txt` as:

- a single numeric value in relative flux units
- rounded to 6 decimal places

Example format:

```text
0.006321
```
