Read `/root/clinic_capacity_input.xlsx` and create a new workbook at `/root/clinic_demand_review.xlsx`.

The output workbook must contain exactly five sheets with these names:

1. `Visits by Zone`
Create a pivot table with:
- Rows: `ServiceZone`
- Values: Sum of `BookedVisits`

2. `Capacity by Zone`
Create a pivot table with:
- Rows: `ServiceZone`
- Values: Sum of `CapacityVisits`

3. `Revenue Gap by Band`
Create a pivot table with:
- Rows: `PressureBand`
- Values: Sum of `RevenueGap`

4. `Gap by Zone and Band`
Create a pivot table with:
- Rows: `ServiceZone`
- Columns: `PressureBand`
- Values: Sum of `RevenueGap`

5. `SourceData`
Create a regular worksheet containing every input row and add these calculated columns:
- `PressureRatio`: `BookedVisits / CapacityVisits`
- `PressureBand`: quartile labels `Q1`, `Q2`, `Q3`, `Q4` based on `PressureRatio` across all rows
- `RevenueGap`: `max(BookedVisits - CapacityVisits, 0) * AvgVisitRevenue`

Rules:
- Keep the original columns and rows in `SourceData`.
- Use the exact quartile labels `Q1`, `Q2`, `Q3`, and `Q4`.
- Save the finished workbook to `/root/clinic_demand_review.xlsx`.
