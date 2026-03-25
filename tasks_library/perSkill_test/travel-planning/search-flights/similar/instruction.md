You are preparing a quick flight-first scouting brief for a travel coordinator.

Input file in `/root/data/`:
1. `similar_roundtrip_requests.json`

Produce this file in `/root/`:
1. `similar_roundtrip_brief.json`

Requirements:
1. Use the bundled flight lookup data instead of memory.
2. Evaluate every candidate option in the input order.
3. For each candidate:
   - Search the exact outbound market and the exact return market for the listed dates.
   - Mark `available` as `true` only if both legs have at least one matching flight.
   - For every available leg, choose the cheapest flight.
   - Break price ties by earlier departure time, then by flight number.
   - Record the chosen leg as an object with:
     - `origin`
     - `destination`
     - `flight_date`
     - `flight_number`
     - `price`
     - `departure_time`
     - `arrival_time`
4. For an unavailable candidate, set `outbound` and `return` to `null`, and set `total_price` to `null`.
5. Write a JSON object with these top-level keys:
   - `request_id`
   - `budget_cap`
   - `evaluated_options`
   - `selected_option`
   - `tool_called`
6. `evaluated_options` must contain one object per candidate with keys:
   - `option_id`
   - `route_label`
   - `available`
   - `outbound`
   - `return`
   - `total_price`
7. `selected_option` must be the cheapest available candidate whose `total_price` is less than or equal to `budget_cap`.
8. Break ties for `selected_option` by earlier outbound departure time, then by `option_id`.
9. If no candidate satisfies the budget, set `selected_option` to `null`.
10. Set `tool_called` to `["search_flights"]`.
