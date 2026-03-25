Read `/root/training_program_input.xlsx` and create a new workbook at `/root/training_grant_dashboard.xlsx`.

The output workbook must contain exactly five sheets with these names:

1. `Participants by Region`
Create a pivot table with:
- Rows: `ProgramRegion`
- Values: Sum of `Participants`

2. `Completed by Track`
Create a pivot table with:
- Rows: `CourseTrack`
- Values: Sum of `CompletedParticipants`

3. `Grant Spend by Region`
Create a pivot table with:
- Rows: `ProgramRegion`
- Values: Sum of `GrantSpend`

4. `Grant Spend by Region Band`
Create a pivot table with:
- Rows: `ProgramRegion`
- Columns: `CompletionBand`
- Values: Sum of `GrantSpend`

5. `SourceData`
Create a regular worksheet containing every input row and add these calculated columns:
- `CompletedParticipants`: round `Participants * CompletionRate` to the nearest whole number
- `CompletionBand`: quartile labels `Q1`, `Q2`, `Q3`, `Q4` based on `CompletionRate` across all rows
- `GrantSpend`: `Participants * GrantPerParticipant`

Rules:
- Keep the original columns and rows in `SourceData`.
- Use the exact quartile labels `Q1`, `Q2`, `Q3`, and `Q4`.
- Save the finished workbook to `/root/training_grant_dashboard.xlsx`.
