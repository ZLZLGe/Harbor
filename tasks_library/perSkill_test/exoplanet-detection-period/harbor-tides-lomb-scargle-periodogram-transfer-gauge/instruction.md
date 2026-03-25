You are given a harbor gauge table at `/root/data/harbor_gauge.csv`.

The file contains these columns:
- `timestamp_utc`: observation time in UTC ISO-8601 format
- `water_level_m`: observed water level in meters
- `sensor_offset_m`: an offset that must be subtracted from `water_level_m` before the search
- `qc_flag`: use only rows with `ok`; ignore other rows

The record contains long maintenance gaps and uneven sampling, but the corrected water level still carries several tidal cycles.

Search the corrected series for periodic signals between `8.0` and `30.0` hours with a sinusoid-plus-constant least-squares periodogram that works on uneven timestamps.

Define the reported power of a candidate period as:
- `1 - RSS / RSS0`
- `RSS` is the residual sum of squares after fitting `sin(2*pi*t/P)`, `cos(2*pi*t/P)`, and a constant term at period `P`
- `RSS0` is the residual sum of squares of the corrected series around its mean

Report the three strongest distinct peaks.
Treat two peaks as distinct only if their periods differ by at least `0.35` hour.
Order the three candidates from strongest to weakest power.

Write `/root/tide_peak_table.csv` with exactly this header:

```csv
rank,period_hours,power
```

Then write exactly three data rows with:
- `rank`: `1`, `2`, `3`
- `period_hours`: the candidate period in hours, rounded to 5 decimal places
- `power`: the candidate power, rounded to 5 decimal places

Only the contents of `/root/tide_peak_table.csv` are graded.
