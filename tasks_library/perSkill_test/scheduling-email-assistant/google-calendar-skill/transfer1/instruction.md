You are auditing local calendar conflicts for facility checks.

Input files in `/root/data/`:
1. `transfer1_facility_checks.json`

Available calendar state in `/root/calendar/`.

Produce this file in `/root/`:
1. `transfer1_conflict_audit.json`

Requirements:
1. For each inspection window in input order, inspect existing calendar events that overlap that window.
2. Write `/root/transfer1_conflict_audit.json` with:
   - `audit_id`
   - `inspections`
   - `tool_called`
3. `inspections` must keep input order and contain:
   - `inspection_id`
   - `overlapping_event_ids`
   - `conflict_count`
4. Set `tool_called` to `["calendar_events_list"]`.
