You are auditing building-access records for an HR security team.

The archived badge packet is stored in `/root/archived_badge_packets.pdf`, and the current clearance workbook is stored in `/root/current_badge_clearance_workbook.xlsx`.

Use the PDF as the older snapshot and compare it with the workbook. The workbook contains these relevant sheets:

- `Badge Roster`: current badge status by employee and badge ID
- `Zone Assignments`: current access zone by badge ID
- `Clearance Registry`: current clearance level by employee ID
- `Policy Matrix`: required clearance level for each access zone

Write `/root/badge_clearance_audit.json` in the following format:

```json
{
  "removed_badges": [
    {
      "employee_id": "EMP2003",
      "badge_id": "BDG-1003"
    }
  ],
  "zone_changes": [
    {
      "employee_id": "EMP2002",
      "badge_id": "BDG-1002",
      "old_zone": "Office West",
      "new_zone": "Research Lab"
    }
  ],
  "clearance_policy_violations": [
    {
      "employee_id": "EMP2005",
      "badge_id": "BDG-1005",
      "zone": "Server Room",
      "required_clearance": "Level 4",
      "actual_clearance": "Level 3"
    }
  ]
}
```

Requirements:

1. Extract the archived badge table from every page of the PDF.
2. Match archived records by `Badge ID` and `Employee ID`.
3. A badge is considered removed if its archived `Badge ID` is missing from `Badge Roster`, or if the current `Badge Status` is anything other than `Active`.
4. Only for badges that are still active, compare the archived `Access Zone` with the current zone from `Zone Assignments` and report differences in `zone_changes`.
5. Only for badges that are still active, compare the employee's current clearance from `Clearance Registry` with the required clearance for the current zone from `Policy Matrix`. If the values are not exactly equal, report the employee in `clearance_policy_violations`.
6. Do not include removed badges in `zone_changes` or `clearance_policy_violations`.
7. Output every value as a string and sort all three lists by `employee_id`.
