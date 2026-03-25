You are checking a local calendar for the earliest feasible proposal slots.

Input files in `/root/data/`:
1. `similar_meeting_windows.json`

Available calendar state in `/root/calendar/`.

Produce this file in `/root/`:
1. `similar_calendar_proposals.json`

Requirements:
1. For each request in input order, inspect existing events inside the request window and choose the earliest available continuous slot whose duration matches `duration_minutes`.
2. Treat existing events as busy from `start` to `end`.
3. Write `/root/similar_calendar_proposals.json` with:
   - `batch_id`
   - `proposals`
   - `tool_called`
4. `proposals` must keep request order and contain:
   - `request_id`
   - `proposed_start`
   - `proposed_end`
5. Set `tool_called` to `["calendar_events_list"]`.
