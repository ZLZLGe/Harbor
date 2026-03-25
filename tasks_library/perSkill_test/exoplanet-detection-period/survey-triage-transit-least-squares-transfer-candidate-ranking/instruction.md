Use the provided transit-search guidance together with the `transitleastsquares` Python package to screen the light curves in `/root/data/survey_targets/`. Each CSV file is one target, and the filename stem is the `target_id` you must report.

Every file contains these columns:
- `time_days`: observation time in days
- `flux`: normalized flux
- `flux_err`: 1-sigma flux uncertainty
- `quality`: cadence quality flag, where `0` means usable data

For each target:
1. Keep only rows with `quality == 0`.
2. Remove flux outliers farther than `5 * 1.4826 * MAD` from the median flux.
3. Detrend the remaining flux by dividing it by a centered rolling median with `window=97` cadences and `min_periods=1`.
4. Run a TLS search on the detrended light curve over periods from `1.5` to `12.0` days. Always pass `flux_err` into TLS. Use the returned best period as `best_period_days`.
5. Use the TLS Signal Detection Efficiency from that same search as `tls_sde`.

Only keep targets with `tls_sde >= 9.0`. These are the convincing candidates for this survey triage pass.

Write `/root/candidate_ranking.csv` with exactly these columns in this order:
- `target_id`
- `best_period_days`
- `tls_sde`

Additional requirements:
- Include exactly one row per convincing candidate
- Sort rows from highest to lowest `tls_sde`
- Round `best_period_days` to `5` decimal places
- Round `tls_sde` to `3` decimal places
- Do not add extra columns

Example format:
```csv
target_id,best_period_days,tls_sde
TG-0001,3.21098,12.442
TG-0002,7.65432,9.107
```
