You are updating local training events in a bundled calendar.

Input files in `/root/data/`:
1. `transfer3_training_updates.json`

Available calendar state in `/root/calendar/`.

Produce this file in `/root/`:
1. `transfer3_update_log.json`

Requirements:
1. Apply every update in input order.
2. Update the listed event's start and end time to the provided values.
3. Write `/root/transfer3_update_log.json` with:
   - `batch_id`
   - `updated_events`
   - `tool_called`
4. `updated_events` must keep input order and contain:
   - `event_id`
   - `new_start`
   - `new_end`
5. Set `tool_called` to `["calendar_events_update"]`.
