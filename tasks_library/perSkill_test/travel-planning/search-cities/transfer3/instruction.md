You are assembling a four-city Florida outreach schedule seed for a mobile services team.

Input file in `/root/data/`:
1. `transfer3_outreach_request.json`

Produce this file in `/root/`:
1. `transfer3_outreach_schedule.json`

Requirements:
1. Use the bundled state-to-city lookup instead of memory.
2. Load all cities for the requested state.
3. Write a JSON object with these top-level keys:
   - `state`
   - `program`
   - `selected_cities`
   - `visit_sequence`
   - `tool_called`
4. `selected_cities` must be an array of exactly 4 objects with keys `slot`, `rule`, and `city`.
5. Fill the slots using these rules:
   - `clinic_anchor`: longest single-word city
   - `weekend_stop`: shortest multiword city
   - `permit_city`: alphabetically earliest city containing the word `City`
   - `comms_backup`: longest city name with a space
6. Measure length after removing spaces.
7. Build `visit_sequence` by sorting the chosen cities first by word count descending and then alphabetically.
8. Set `tool_called` to `["search_cities"]`.
