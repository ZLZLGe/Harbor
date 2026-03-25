You are given an unevenly sampled stellar light curve at `/root/data/starspot_lightcurve.csv`.

The file contains these columns:
- `time_day`: observation time in days
- `relative_flux`: normalized flux
- `flux_err`: 1-sigma flux uncertainty
- `quality_flag`: `0` means usable data, nonzero values should be discarded

This star shows rotational modulation from starspots. The light curve also contains a small number of flare-like outliers that are not marked by the quality flag. Clean the unusable points, suppress the obvious flare outliers, and recover the star's dominant rotation period.

Write the final period in days to `/root/rotation_period.txt` as:
- exactly one numeric value
- rounded to 5 decimal places
- no extra text

Example:
```text
8.73400
```
