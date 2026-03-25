You are given an uneven radial-velocity visit table at `/root/data/rv_visits.csv`.

The file contains these columns:
- `bjd_day`: observation time in days
- `rv_mps`: measured stellar radial velocity in m/s
- `rv_err_mps`: 1-sigma radial-velocity uncertainty in m/s
- `template_drift_mps`: an instrumental drift estimate that should be subtracted from `rv_mps` before the period search
- `status`: use only rows with `keep`; ignore rows with `drop`

Search the cleaned radial-velocity series for periodic signals between `0.6` and `8.0` days, using the measurement uncertainties during the search.

Report:
- the strongest periodogram peak as the primary period
- the next two strongest distinct peaks as alternate candidates

Treat two peaks as distinct only if their periods differ by at least `0.2` day. The alternate candidates must be ordered by decreasing peak power.

Write `/root/rv_period_report.json` as a JSON object with exactly these keys:
- `primary_period_days`
- `alternate_periods_days`

Requirements:
- `primary_period_days` must be one positive JSON number
- `alternate_periods_days` must be an array of exactly two positive JSON numbers
- round every reported period to 5 decimal places
- do not write any extra text outside the JSON file

Example:
```json
{
  "primary_period_days": 3.72939,
  "alternate_periods_days": [0.78809, 1.36517]
}
```
