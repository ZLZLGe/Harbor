# Transfer: Disaster Retrofit Replanner

## Task

You are repairing a damaged Civilization VI city plan after a disaster.

Read the scenario file at:
- `/data/disaster_retrofit_basin/scenario.json`

The scenario gives you:
- one fixed city center,
- the city's current district layout before the repair,
- a list of districts that are allowed to move,
- a rebuild move budget,
- a set of disabled tiles that cannot be used anymore,
- the full tile list for this micro-map.

Your job is to produce the best legal retrofit plan:
1. Keep every locked district on its current tile.
2. Reposition only the allowed movable districts.
3. Respect the move budget.
4. Avoid every disabled tile.
5. Recalculate the final district adjacency exactly.

Only the listed tiles exist.

## Output

Write your answer to:
- `/output/retrofit_plan.json`

Use this JSON structure:

```json
{
  "city_center": [6, 4],
  "final_districts": {
    "AQUEDUCT": [5, 4],
    "DAM": [6, 5],
    "INDUSTRIAL_ZONE": [5, 5],
    "HARBOR": [7, 4],
    "NEIGHBORHOOD": [4, 5],
    "CAMPUS": [5, 3],
    "COMMERCIAL_HUB": [7, 5]
  },
  "moved_districts": {
    "CAMPUS": {"from": [6, 3], "to": [5, 3]},
    "COMMERCIAL_HUB": {"from": [7, 3], "to": [7, 5]}
  },
  "district_adjacency": {
    "AQUEDUCT": 0,
    "DAM": 0,
    "INDUSTRIAL_ZONE": 6,
    "HARBOR": 4,
    "NEIGHBORHOOD": 0,
    "CAMPUS": 3,
    "COMMERCIAL_HUB": 4
  },
  "total_adjacency": 17
}
```

## Requirements

1. Output valid JSON.
2. `city_center` must exactly match the scenario's fixed city center.
3. `final_districts` must contain exactly the same district names as `existing_districts` in the scenario, with no extras and no omissions.
4. Every district not listed in `movable_districts` must stay on its original tile.
5. `moved_districts` must contain exactly the districts whose final tile differs from the original tile.
6. Every key in `moved_districts` must be listed in `movable_districts`.
7. The number of moved districts must be at most `move_budget`.
8. No final district may be placed on a disabled tile.
9. All final district placements must obey Civ6 placement rules and must not overlap.
10. `district_adjacency` must contain one integer entry for every district in `final_districts`.
11. `total_adjacency` must equal the sum of all values in `district_adjacency`.
12. The reported adjacency values must be accurate.

## Goal

Maximize the final `total_adjacency`.
