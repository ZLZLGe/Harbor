Use the provided starting workbook in `/root/data` as the base file. Keep the existing sheets and structure intact, build the audit with spreadsheet formulas, and save the completed workbook in `/root/output` using the task's required result filename.

Requirements:
1. Do the reconciliation inside the workbook. Do not replace the review sheet with values calculated in Python or another scripting language.
2. Preserve the existing sheet names and the student order already listed on `Award Review`.
3. Use formulas so the workbook remains recalculable after it is saved.

Step 1:
- In `Award Review`, fill `B11:E18` for the student IDs already listed in `A11:A18`.
- Pull each student name and roster tier from `Student Roster`.
- Use the rows in `Term Grades` to calculate:
  - passed credits in column `D`
  - term GPA in column `E` as total quality points divided by total attempted credits

Step 2:
- In `Award Review!F11:F18`, determine the highest earned tier for each student using `Award Rules`:
  - `Dean` if both the GPA threshold and passed-credit threshold for `Dean` are met
  - otherwise `Merit` if both `Merit` thresholds are met
  - otherwise `Access` if both `Access` thresholds are met
  - otherwise `Ineligible`
- In `G11:G18`, mark bursar status as `Cleared` only when all of these are true:
  - outstanding balance is at most `500`, or `Payment Plan Active` is `Yes`
  - `Hold Code` is `None`
  - `Refund Account On File` is `Yes`
- In `H11:H18`, classify each row as:
  - `Academic Ineligible` when the earned tier is `Ineligible`
  - `Match` when earned tier matches the roster tier
  - `Mismatch` otherwise

Step 3:
- In `I11:I18`, assign final status:
  - `Approve` when the row is a `Match` and bursar status is `Cleared`
  - `Manual Review` when the row is a `Mismatch` and bursar status is `Cleared`
  - `Hold` otherwise
- In `J11:J18`, return the roster-tier award amount from `Award Rules` only for rows with final status `Approve`; otherwise return `0`.
- Complete summary cells `C3:C7` on `Award Review` with formulas for:
  - total nominated students
  - count of students who earned any tier
  - count of mismatches
  - count of bursar holds
  - total approved disbursement amount
