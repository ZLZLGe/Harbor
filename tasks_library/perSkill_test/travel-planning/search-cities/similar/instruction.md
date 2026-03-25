You are preparing a three-city Ohio route seed that will be handed to a fuller road-trip planner.

Input file in `/root/data/`:
1. `similar_trip_request.json`

Produce this file in `/root/`:
1. `similar_trip_city_shortlist.json`

Requirements:
1. Use the bundled state-to-city lookup instead of memory.
2. Load all cities for the requested state.
3. Write a JSON object with these top-level keys:
   - `state`
   - `trip_days`
   - `selected_cities`
   - `route_order`
   - `tool_called`
4. `selected_cities` must be an array of exactly 3 objects with keys `slot`, `rule`, and `city`.
5. Fill the slots using these rules:
   - `anchor_city`: alphabetically earliest city whose name starts with `C`
   - `connector_city`: longest city name containing the letter `o` (ignore spaces when measuring length)
   - `buffer_city`: alphabetically last city whose name has exactly 6 letters (ignore spaces)
6. Build `route_order` by sorting the chosen cities by normalized length ascending, breaking ties alphabetically.
7. Set `tool_called` to `["search_cities"]`.
