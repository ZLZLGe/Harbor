Read `/root/retail_territory_input.xlsx` and create a new workbook at `/root/retail_margin_pack.xlsx`.

The output workbook must contain exactly five sheets with these names:

1. `Orders by Territory`
Create a pivot table with:
- Rows: `Territory`
- Values: Sum of `Orders`

2. `Net Revenue by Format`
Create a pivot table with:
- Rows: `StoreFormat`
- Values: Sum of `NetRevenue`

3. `Promo Spend by Territory`
Create a pivot table with:
- Rows: `Territory`
- Values: Sum of `PromoSpend`

4. `Net Revenue by Territory Band`
Create a pivot table with:
- Rows: `Territory`
- Columns: `ReturnBand`
- Values: Sum of `NetRevenue`

5. `SourceData`
Create a regular worksheet containing every input row and add these calculated columns:
- `GrossRevenue`: `Orders * AvgTicket`
- `ReturnBand`: quartile labels `Q1`, `Q2`, `Q3`, `Q4` based on `ReturnRate` across all rows
- `NetRevenue`: `(Orders * AvgTicket * (1 - ReturnRate)) - PromoSpend`

Rules:
- Keep the original columns and rows in `SourceData`.
- Use the exact quartile labels `Q1`, `Q2`, `Q3`, and `Q4`.
- Save the finished workbook to `/root/retail_margin_pack.xlsx`.
