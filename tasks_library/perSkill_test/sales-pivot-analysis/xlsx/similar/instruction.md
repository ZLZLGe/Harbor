Read `/root/income.xlsx` and create a new workbook at `/root/income_band_review.xlsx`.

The output workbook must contain exactly five sheets with these names:

1. `Earners by Band`
Create a pivot table with:
- Rows: `IncomeBand`
- Values: Sum of `EARNERS`

2. `Median Income by Prefix`
Create a pivot table with:
- Rows: `SA2_PREFIX`
- Values: Average of `MEDIAN_INCOME`

3. `Mean Income by Band`
Create a pivot table with:
- Rows: `IncomeBand`
- Values: Average of `MEAN_INCOME`

4. `Payroll by Prefix Band`
Create a pivot table with:
- Rows: `SA2_PREFIX`
- Columns: `IncomeBand`
- Values: Sum of `EstimatedPayroll`

5. `SourceData`
Create a regular worksheet containing every row from the input workbook and add these calculated columns:
- `SA2_PREFIX`: the first three digits of `SA2_CODE`
- `IncomeBand`: quartile labels `Q1`, `Q2`, `Q3`, `Q4` based on `MEDIAN_INCOME` across all rows
- `EstimatedPayroll`: `EARNERS * MEDIAN_INCOME`

Rules:
- Keep the original columns and rows in `SourceData`.
- The quartile labels must use the exact strings `Q1`, `Q2`, `Q3`, and `Q4`.
- Save the finished workbook to `/root/income_band_review.xlsx`.
