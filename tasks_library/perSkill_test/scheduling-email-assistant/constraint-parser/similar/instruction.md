You are preparing a scheduling-constraints digest for a coordinator.

Input file in `/root/data/`:
1. `similar_meeting_requests.json`

Produce this file in `/root/`:
1. `similar_constraints_digest.json`

Requirements:
1. Read every request in the input order.
2. Write one object per request under `parsed_requests`.
3. Each parsed request object must contain:
   - `request_id`
   - `requester_email`
   - `meeting_duration_minutes`
   - `allowed_dates`
   - `time_window`
   - `blocked_windows`
   - `notes`
4. `time_window` must be an object with `start` and `end` in `HH:MM` 24-hour format.
5. `blocked_windows` must be a list of objects with `date`, `start`, and `end`.
6. Preserve the listed date order for `allowed_dates`.
7. Preserve the listed note order for `notes`.
8. Write a top-level JSON object with keys:
   - `batch_id`
   - `parsed_requests`
   - `tool_called`
9. Set `tool_called` to `["constraint_parser"]`.
