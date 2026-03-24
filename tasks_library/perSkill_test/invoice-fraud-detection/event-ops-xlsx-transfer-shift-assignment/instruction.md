Use the workbook template in `/root/` whose basename is `event_shift_template` as the starting file. Save the completed result in `/root/` with basename `event_shift_plan` and the same workbook suffix as the starting file.

The workbook contains these sheets:
- `Volunteer Roster`: volunteer details and per-person `max_shifts`
- `Availability Matrix`: one row per volunteer and one column per `shift_id`
- `Role Qualifications`: role eligibility matrix by volunteer
- `Shift Demand`: staffing requests to process in sheet order
- `Assignments`: output sheet you must populate
- `Coverage Summary`: output sheet you must populate

Assignment rules:
- Process `Shift Demand` from top to bottom.
- For each demand row, fill the requested slots one at a time in slot order starting from `1`.
- A volunteer is eligible for a slot only if all of the following are true:
  - the volunteer is marked `Y` for that `shift_id` in `Availability Matrix`
  - the volunteer is marked `Y` for that `role` in `Role Qualifications`
  - the volunteer has not already reached `max_shifts`
  - the volunteer is not already assigned anywhere else in the same `shift_id`
- When more than one volunteer is eligible, choose the volunteer using this exact priority order:
  1. fewer assignments already given in the workbook so far
  2. smaller `assignment_rank`
  3. alphabetical `volunteer_id`

Populate `Assignments` starting at row 3 with exactly these columns:
`shift_id`, `shift_date`, `zone`, `role`, `slot_number`, `volunteer_id`, `volunteer_name`, `team`

Populate `Coverage Summary` starting at row 3 with exactly these columns:
`shift_id`, `shift_date`, `zone`, `role`, `required_count`, `assigned_count`, `gap_count`, `status`

Coverage rules:
- `assigned_count` is the number of slots you actually filled for that demand row.
- `gap_count` is `required_count - assigned_count`.
- `status` must be `Covered` when `gap_count` is `0`, otherwise `Understaffed`.

Additional requirements:
- Keep the note in cell `A1` and the header row in row 2 unchanged on both output sheets.
- Keep `Volunteer Roster`, `Availability Matrix`, `Role Qualifications`, and `Shift Demand` unchanged.
- Keep the existing sheet order unchanged.
- Save the finished workbook in `/root/` with basename `event_shift_plan` and the same workbook suffix as the starting file.
