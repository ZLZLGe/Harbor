# Transfer - Rover Route Batch Ranking

You are given route telemetry at `/root/data/routes.csv`.

Evaluate every policy combination from:
- `inspect_interval`: 15, 20, 25, 30
- `crew_size`: 2, 3, 4
- `drone_share`: 0.1, 0.3, 0.5, 0.7

For each policy, score all routes using the deterministic route-scoring equations implied by the dataset schema, then aggregate:
- `total_score`
- `total_delay`

Rank all policies by:
1. `total_score` descending
2. `total_delay` ascending
3. then lexical tie-break by the parameter tuple

Write exactly one CSV file:
- `/outputs/transfer1_route_rankings.csv`

CSV schema and order:
- `rank,inspect_interval,crew_size,drone_share,total_score,total_delay`

Output only the top 6 ranked rows.

Formatting rules:
- `drone_share` rounded to 1 decimal place
- `total_score` and `total_delay` rounded to 4 decimal places
- `rank` starts at 1 and increments by 1
