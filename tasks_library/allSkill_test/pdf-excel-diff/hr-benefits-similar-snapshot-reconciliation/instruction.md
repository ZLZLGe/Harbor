You are reconciling employee benefits records for an HR team.

The archived enrollment snapshot is stored in `/root/archived_benefits_snapshot.pdf`, and the current enrollment workbook is stored in `/root/current_benefits_enrollment.xlsx`.

Use the archived PDF as the older source of truth and compare it with the current Excel workbook. Match records by `Employee ID`, then write `/root/benefits_enrollment_diff.json` in the following format:

```json
{
  "removed_employees": ["BEN0005", "BEN0012"],
  "tier_changes": [
    {
      "employee_id": "BEN0002",
      "old_tier": "Employee Only",
      "new_tier": "Employee + Spouse"
    }
  ],
  "dependent_count_changes": [
    {
      "employee_id": "BEN0003",
      "old_dependents": 0,
      "new_dependents": 1
    }
  ],
  "salary_band_changes": [
    {
      "employee_id": "BEN0004",
      "old_salary_band": "Band B",
      "new_salary_band": "Band C"
    }
  ]
}
```

Requirements:

1. Extract the employee table from every page of the archived PDF.
2. Compare the archived snapshot with the current workbook by `Employee ID`.
3. Report employees who appear in the archived PDF but not in the current workbook under `removed_employees`.
4. Report only these field-level changes for employees present in both files:
   - `Plan Tier` -> `tier_changes`
   - `Dependent Count` -> `dependent_count_changes`
   - `Salary Band` -> `salary_band_changes`
5. Output `Dependent Count` values as numbers.
6. Output all tier and salary-band values as strings.
7. Sort `removed_employees` and every change list by `employee_id` for deterministic output.
