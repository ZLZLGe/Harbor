You are reviewing training compliance records for an HR operations team.

The archived completion roster is stored in `/root/archived_training_rosters.pdf`, and the current workbook is stored in `/root/current_training_compliance_tracker.xlsx`.

Use the PDF as the older snapshot and compare it with the workbook. The workbook contains these relevant sheets:

- `Compliance Tracker`: the current employee-course records with the columns `Employee ID`, `Employee Name`, `Course Code`, `Tracker Status`, and `Renewal Date`
- `Status Guide`: the mapping from each `Tracker Status` value to its normalized status label and severity rank

Write `/root/training_compliance_discrepancies.json` in the following format:

```json
{
  "dropped_employees": [
    {
      "employee_id": "EMP3003",
      "employee_name": "Carla Ruiz"
    }
  ],
  "status_regressions": [
    {
      "employee_id": "EMP3002",
      "employee_name": "Ben Ortiz",
      "course_code": "HAZ-201",
      "archived_status": "Current",
      "current_status": "Grace Period"
    }
  ],
  "renewal_date_mismatches": [
    {
      "employee_id": "EMP3004",
      "employee_name": "Dina Shah",
      "course_code": "FORK-110",
      "archived_renewal_date": "2026-09-30",
      "current_renewal_date": "2026-10-31"
    }
  ]
}
```

Requirements:

1. Extract every training row from every page of the archived PDF.
2. Use `Employee ID` + `Course Code` as the record key when comparing individual certifications.
3. Treat an employee as dropped only when their `Employee ID` appears in the archived PDF but does not appear anywhere in `Compliance Tracker`.
4. Normalize archived PDF statuses with these rules before comparing them:
   - `Complete` -> `Current`
   - `Grace` -> `Grace Period`
   - `Expired` -> `Expired`
5. Normalize current workbook statuses by looking them up in `Status Guide`, and use the guide's severity rank to determine regressions.
6. A status regression occurs when the current normalized status rank is lower than the archived normalized status rank for the same `Employee ID` + `Course Code`.
7. A renewal-date mismatch occurs when the same `Employee ID` + `Course Code` exists in both sources but the normalized renewal dates are different.
8. Output renewal dates in `YYYY-MM-DD` format.
9. Ignore workbook rows that do not exist in the archived PDF.
10. Sort `dropped_employees` by `employee_id`, and sort the other two lists by `employee_id` then `course_code`.
