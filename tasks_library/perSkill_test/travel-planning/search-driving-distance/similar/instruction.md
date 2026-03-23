You are reviewing driving-only route options for a weeklong Ohio road trip that starts and ends in Minneapolis.

Input file in `/root/data/`:
1. `similar_route_candidates.json`

Produce this file in `/root/`:
1. `similar_route_recommendation.json`

Requirements:
1. Use the bundled city-to-city ground-distance lookup instead of memory.
2. Treat every candidate as a complete loop: start city -> listed stops in order -> start city.
3. Use driving mode for every leg.
4. Write a JSON object with these top-level keys:
   - `start_city`
   - `recommended_route_id`
   - `recommended_route_stops`
   - `recommended_legs`
   - `route_summaries`
   - `tool_called`
5. Each item in `recommended_legs` must contain:
   - `leg_number`
   - `origin`
   - `destination`
   - `duration_minutes`
   - `distance_km`
   - `estimated_cost`
6. Each item in `route_summaries` must contain:
   - `route_id`
   - `ordered_stops`
   - `total_duration_minutes`
   - `total_distance_km`
   - `total_estimated_cost`
   - `leg_count`
7. Choose `recommended_route_id` by the lowest `total_duration_minutes`. Break ties by lower `total_distance_km`, then alphabetically by `route_id`.
8. `recommended_route_stops` must be the stop list for the chosen route.
9. `tool_called` must list the bundled lookup tool that was used to build the recommendation.
