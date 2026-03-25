You are preparing the meal portion of a short Ohio road trip.

Input file in `/root/data/`:
1. `similar_trip_request.json`

Use the bundled city restaurant lookup instead of memory.

Produce this file in `/root/`:
1. `similar_dining_route.json`

Requirements:
1. For each requested stop, search restaurants for the specified city.
2. Keep only restaurants whose cuisine list contains the requested cuisine substring, case-insensitively.
3. Enforce the per-stop `max_average_cost` and `min_aggregate_rating` filters.
4. Choose exactly one restaurant per stop using this ranking:
   - lowest `Average Cost`
   - then highest `Aggregate Rating`
   - then restaurant name alphabetically
5. Write a JSON object with these top-level keys:
   - `trip_name`
   - `stops`
   - `total_average_cost`
   - `tool_called`
6. `stops` must preserve the order from the request file.
7. Each stop object must contain:
   - `slot`
   - `city`
   - `requested_cuisine`
   - `restaurant_name`
   - `average_cost`
   - `aggregate_rating`
8. Set `tool_called` to `["search_restaurants"]`.
