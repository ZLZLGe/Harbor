You are given two employee workbooks:

- Archived workbook: `/root/employee_records_archive.xlsx`
- Current workbook: `/root/employee_records_current.xlsx`

Each workbook contains extra sheets and non-table rows. Find the worksheet that contains the employee roster in each file, compare the records by `Employee ID`, and write a JSON report to `/root/employee_workbook_diff.json`.

The report must use this shape:

```json
{
  "deleted_employee_ids": ["EMP00105", "EMP00109"],
  "modified_fields": [
    {
      "employee_id": "EMP00101",
      "field": "Salary",
      "old_value": 92000,
      "new_value": 96000
    }
  ]
}
```

Requirements:

1. `deleted_employee_ids` must contain employees that exist in the archived workbook but not in the current workbook.
2. `modified_fields` must contain one entry for every changed field for employees that exist in both workbooks.
3. Ignore employees that are new in the current workbook.
4. Use the field names exactly as they appear in the roster headers.
5. Normalize values before comparing:
   - Trim surrounding whitespace from text cells.
   - Treat numeric strings and numeric cells with the same value as equal.
6. For `Salary` and `Bonus %`, write JSON numbers. For all other fields, write JSON strings.
7. Sort `deleted_employee_ids` ascending.
8. Sort `modified_fields` by `employee_id`, then by `field`.
