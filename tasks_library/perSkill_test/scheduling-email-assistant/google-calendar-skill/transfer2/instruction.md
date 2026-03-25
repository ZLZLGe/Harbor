You are creating approved interview holds in a local calendar.

Input files in `/root/data/`:
1. `transfer2_interview_holds.json`

Available calendar state in `/root/calendar/`.

Produce this file in `/root/`:
1. `transfer2_created_holds.json`

Requirements:
1. Create one event per hold request in input order.
2. Use the provided summary, start, and end values exactly.
3. Write `/root/transfer2_created_holds.json` with:
   - `batch_id`
   - `created_events`
   - `tool_called`
4. `created_events` must keep input order and contain:
   - `request_id`
   - `event_id`
5. Set `tool_called` to `["calendar_events_create"]`.
