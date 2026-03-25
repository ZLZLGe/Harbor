You are screening same-day connection options from a bundled flight database.

Input file in `/root/data/`:
1. `transfer3_connection_candidates.json`

Produce this file in `/root/`:
1. `transfer3_connection_screen.json`

Requirements:
1. Use the bundled flight lookup data instead of memory.
2. Respect the layover window from the input file:
   - `minimum_layover_minutes`
   - `maximum_layover_minutes`
3. Evaluate every candidate connection in input order.
4. For each candidate:
   - search the exact first-leg market and the exact second-leg market for the listed travel date
   - consider every pair of returned flights
   - a pair is feasible only when the second-leg departure is at least the minimum layover after the first-leg arrival and no more than the maximum layover after the first-leg arrival
5. For each candidate summary, write:
   - `connection_id`
   - `travel_date`
   - `first_leg_route`
   - `second_leg_route`
   - `status`
   - `feasible_connection_count`
   - `best_connection`
6. Set `status` to `FEASIBLE` when at least one pair passes the layover window; otherwise set it to `NO_FEASIBLE_CONNECTION`.
7. When a candidate is feasible, `best_connection` must contain:
   - `first_leg_flight_number`
   - `second_leg_flight_number`
   - `first_leg_departure`
   - `first_leg_arrival`
   - `second_leg_departure`
   - `second_leg_arrival`
   - `layover_minutes`
   - `total_price`
8. Choose `best_connection` by lowest `total_price`, then by lower `layover_minutes`, then by earlier `first_leg_departure`, then by flight numbers.
9. For an infeasible candidate, set `best_connection` to `null` and `feasible_connection_count` to `0`.
10. Write a JSON object with these top-level keys:
   - `analysis_id`
   - `minimum_layover_minutes`
   - `maximum_layover_minutes`
   - `candidate_summaries`
   - `selected_connection`
   - `tool_called`
11. `selected_connection` must be the cheapest candidate-level `best_connection` among all feasible candidates.
12. Break ties for `selected_connection` by lower `layover_minutes`, then by `connection_id`.
13. If every candidate is infeasible, set `selected_connection` to `null`.
14. Set `tool_called` to `["search_flights"]`.
