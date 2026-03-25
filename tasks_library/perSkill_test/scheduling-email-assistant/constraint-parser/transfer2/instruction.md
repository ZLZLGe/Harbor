You are consolidating candidate interview constraints.

Input file in `/root/data/`:
1. `transfer2_candidate_availability.csv`

Produce this file in `/root/`:
1. `transfer2_interview_constraints.json`

Requirements:
1. Read every candidate row in file order.
2. Write one object per candidate under `candidates`.
3. Each object must contain:
   - `candidate_id`
   - `candidate_name`
   - `stage`
   - `interview_length_minutes`
   - `allowed_dates`
   - `time_window`
   - `blocked_windows`
   - `notes`
4. `time_window` must be an object with `start` and `end` in `HH:MM` 24-hour format.
5. `blocked_windows` must be a list of objects with `date`, `start`, and `end`.
6. Write a top-level JSON object with keys:
   - `campaign_id`
   - `candidates`
   - `tool_called`
7. Set `tool_called` to `["constraint_parser"]`.
