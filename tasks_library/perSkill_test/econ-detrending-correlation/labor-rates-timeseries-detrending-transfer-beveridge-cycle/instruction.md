The Beveridge curve studies how unemployment and labor demand move against each other over the cycle. For this task you will work with a monthly U.S. dataset that has already been assembled.

Goal: Using `/root/us_beveridge_monthly.csv`, compute the Pearson correlation between the cyclical components of the unemployment rate and the job openings rate for 2001-01 through 2024-12.

The CSV has one row per month with these columns:
- `month`
- `unemployment_rate`
- `job_openings_rate`
- `regime_tag`

Requirements:
1. Use all rows in the file, covering 2001-01 to 2024-12.
2. The two series are already rates in percent, so filter them directly in levels. Do not take natural logs.
3. Apply the Hodrick-Prescott filter with `lambda = 129600`, the standard choice for monthly data.
4. Compute the contemporaneous Pearson correlation between the two cyclical components.
5. Write the result to `/root/beveridge-cycle-corr.txt`.
6. The output file must contain only the correlation coefficient as a single number, rounded to 5 decimal places.

Example output:
```text
-0.12345
```
