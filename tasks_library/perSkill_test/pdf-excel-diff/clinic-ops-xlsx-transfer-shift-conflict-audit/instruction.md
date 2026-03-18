You are given a clinic staffing workbook at `/root/clinic_staffing.xlsx`.

The workbook includes three relevant worksheets:

- `Availability`: staff blackout periods
- `Assignments`: staff scheduled onto clinic shifts
- `Room Coverage`: required staffing for each shift

Inspect the workbook and write `/root/clinic_shift_conflicts.json` using this exact shape:

```json
{
  "double_booked_staff": [
    {
      "staff_id": "S-003",
      "staff_name": "Ava Lin",
      "date": "2026-04-14",
      "first_shift_id": "CL-1003",
      "first_room": "Lab A",
      "first_start_time": "09:30",
      "first_end_time": "13:00",
      "second_shift_id": "CL-1004",
      "second_room": "Imaging",
      "second_start_time": "12:00",
      "second_end_time": "16:00"
    }
  ],
  "unavailable_assignments": [
    {
      "shift_id": "CL-1006",
      "staff_id": "S-005",
      "staff_name": "Maya Gomez",
      "date": "2026-04-15",
      "room": "Pediatrics",
      "shift_start_time": "08:00",
      "shift_end_time": "12:00",
      "unavailable_start_time": "10:00",
      "unavailable_end_time": "12:00"
    }
  ],
  "uncovered_shifts": [
    {
      "shift_id": "CL-1005",
      "date": "2026-04-14",
      "room": "Triage",
      "start_time": "13:00",
      "end_time": "17:00",
      "required_staff": 2,
      "assigned_staff": 1,
      "missing_staff": 1
    }
  ]
}
```

Rules:

1. Match rows across worksheets by `Shift ID` and by `Staff ID` where applicable.
2. A staff member is double-booked when two assigned shifts for the same person occur on the same date and their time windows overlap. If one shift ends exactly when the other starts, do not treat that as an overlap.
3. An assignment is unavailable when the assigned shift overlaps any blackout period for the same staff member on the same date.
4. A shift is uncovered when the number of assignment rows for that `Shift ID` is lower than the `Required Staff` value in `Room Coverage`.
5. Use `YYYY-MM-DD` for dates and `HH:MM` for times in the JSON output.
6. Use JSON numbers for staffing counts.
7. Sort `double_booked_staff` by `staff_id`, `date`, `first_shift_id`, `second_shift_id`.
8. Sort `unavailable_assignments` by `shift_id`, then `staff_id`.
9. Sort `uncovered_shifts` by `shift_id`.
