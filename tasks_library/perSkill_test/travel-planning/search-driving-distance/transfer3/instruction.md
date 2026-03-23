You are auditing whether roundtrip repositioning lanes behave symmetrically enough for weekly fleet planning.

Input file in `/root/data/`:
1. `transfer3_roundtrip_lanes.json`

Produce this file in `/root/`:
1. `transfer3_lane_balance_report.json`

Requirements:
1. Use the bundled city-to-city ground-distance lookup instead of memory.
2. Use driving mode for every outbound and return lookup.
3. Write a JSON object with these top-level keys:
   - `most_balanced_lane_id`
   - `lane_rankings`
   - `tool_called`
4. Each item in `lane_rankings` must contain:
   - `lane_id`
   - `city_a`
   - `city_b`
   - `outbound_duration_minutes`
   - `return_duration_minutes`
   - `duration_delta_minutes`
   - `outbound_distance_km`
   - `return_distance_km`
   - `distance_delta_km`
5. Sort `lane_rankings` by `duration_delta_minutes` ascending, then `distance_delta_km` ascending, then `lane_id`.
6. `most_balanced_lane_id` must be the first lane after that ordering.
7. `tool_called` must list the bundled lookup tool that was used to build the audit.
