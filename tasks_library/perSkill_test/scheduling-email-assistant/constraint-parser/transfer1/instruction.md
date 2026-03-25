You are converting shift-swap notes into a planning board.

Input file in `/root/data/`:
1. `transfer1_shift_notes.json`

Produce this file in `/root/`:
1. `transfer1_shift_constraints.json`

Requirements:
1. Read every ticket in input order.
2. Write one object per ticket under `swap_requests`.
3. Each object must contain:
   - `ticket_id`
   - `employee`
   - `site`
   - `minimum_shift_hours`
   - `must_cover`
   - `cannot_cover`
   - `notes`
4. `must_cover` and `cannot_cover` must stay in the listed order.
5. Write a top-level JSON object with keys:
   - `board_id`
   - `swap_requests`
   - `tool_called`
6. Set `tool_called` to `["constraint_parser"]`.
