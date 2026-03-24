You are given a normalized survey light curve for a detached eclipsing binary at `/root/data/eclipsing_binary_survey.csv` with the columns:

- `time_bjd`
- `relative_flux`
- `flux_err`
- `visit_id`

The light curve contains repeated primary and secondary eclipses plus a small amount of residual variability and a few outliers.

Determine the orbital period of the binary system and write it to `/root/binary_period.txt` in the following format:

- A single numerical value in days
- Round the value to 5 decimal places

Example:
```text
3.18472
```
