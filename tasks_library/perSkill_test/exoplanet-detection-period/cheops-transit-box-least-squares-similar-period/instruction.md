You are given a baseline-corrected CHEOPS light curve at `/root/data/cheops_gapped_lc.csv` with the columns:

- `time_bjd`
- `normalized_flux`
- `flux_err`

The series has already been quality filtered, but it still contains long gaps between visits and a shallow repeating transit signal from a planet candidate.

Determine the orbital period of the candidate planet and write it to `/root/planet_period.txt` with the following format:

- A single numerical value in days
- Round the value to 5 decimal places

Example:
```text
3.74216
```
