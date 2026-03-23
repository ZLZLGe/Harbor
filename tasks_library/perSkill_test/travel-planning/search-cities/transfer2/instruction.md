You are assembling a four-lane California mutual-aid coverage handoff.

Input file in `/root/data/`:
1. `transfer2_coverage_request.json`

Produce this file in `/root/`:
1. `transfer2_service_coverage.json`

Requirements:
1. Use the bundled state-to-city lookup instead of memory.
2. Load all cities for the requested state.
3. Write a JSON object with these top-level keys:
   - `state`
   - `mission`
   - `selected_cities`
   - `inspection_order`
   - `tool_called`
4. `selected_cities` must be an array of exactly 4 objects with keys `slot`, `rule`, and `city`.
5. Fill the slots using these rules:
   - `san_lane`: alphabetically earliest city starting with `San `
   - `santa_lane`: alphabetically latest city starting with `Santa `
   - `oak_lane`: shortest single-word city containing the letter `k`
   - `southern_backup`: alphabetically earliest multiword city starting with `L`
6. Measure length after removing spaces.
7. Build `inspection_order` by sorting the chosen cities by normalized length ascending, breaking ties alphabetically.
8. Set `tool_called` to `["search_cities"]`.
