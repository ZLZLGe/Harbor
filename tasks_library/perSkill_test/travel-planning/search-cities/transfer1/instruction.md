You are selecting four Texas hub cities for a field mentor roadshow.

Input file in `/root/data/`:
1. `transfer1_training_request.json`

Produce this file in `/root/`:
1. `transfer1_training_hubs.json`

Requirements:
1. Use the bundled state-to-city lookup instead of memory.
2. Load all cities for the requested state.
3. Write a JSON object with these top-level keys:
   - `state`
   - `program`
   - `selected_cities`
   - `rotation_order`
   - `tool_called`
4. `selected_cities` must be an array of exactly 4 objects with keys `slot`, `rule`, and `city`.
5. Fill the slots using these rules:
   - `campus_anchor`: alphabetically earliest two-word city among the longest two-word city names in the state
   - `drive_through_stop`: shortest city ending with `o`
   - `coastal_gateway`: alphabetically earliest city starting with `B`
   - `backup_single_word`: longest single-word city not already selected
6. Measure length after removing spaces.
7. Build `rotation_order` by sorting the chosen cities by normalized length ascending, breaking ties alphabetically.
8. Set `tool_called` to `["search_cities"]`.
