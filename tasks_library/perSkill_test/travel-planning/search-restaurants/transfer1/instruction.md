You are preparing a dining feasibility brief for a client workshop.

Input file in `/root/data/`:
1. `transfer1_host_request.json`

Use the bundled city restaurant lookup instead of memory.

Produce this file in `/root/`:
1. `transfer1_host_city_brief.json`

Requirements:
1. Search restaurants separately for every candidate city.
2. For each target cuisine, keep only restaurants whose cuisine list contains that cuisine substring, case-insensitively.
3. Exclude restaurants whose `Average Cost` exceeds `max_average_cost`.
4. For every city and cuisine, if multiple restaurants qualify, choose one using:
   - lowest `Average Cost`
   - then highest `Aggregate Rating`
   - then restaurant name alphabetically
5. Write a JSON object with these top-level keys:
   - `brief_name`
   - `recommended_city`
   - `city_summaries`
   - `tool_called`
6. `city_summaries` must preserve the order from the request file.
7. Each city summary must contain:
   - `city`
   - `covered_cuisine_count`
   - `missing_cuisines`
   - `estimated_bundle_cost`
   - `bundle`
8. Each `bundle` item must contain:
   - `cuisine`
   - `restaurant_name`
   - `average_cost`
   - `aggregate_rating`
9. Choose `recommended_city` by:
   - highest `covered_cuisine_count`
   - then lowest `estimated_bundle_cost`
   - then city name alphabetically
10. Set `tool_called` to `["search_restaurants"]`.
