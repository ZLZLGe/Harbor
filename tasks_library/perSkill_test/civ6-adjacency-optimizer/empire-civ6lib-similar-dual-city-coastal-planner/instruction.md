# Similar: Dual-City Coastal Expansion Planner

## Task

Plan a two-city coastal empire for a fixed Civilization VI micro-scenario.

The scenario file is located at:
- `/data/coastal_empire/scenario.json`

Each city role has:
- a fixed population,
- a small set of candidate city-center tiles,
- an exact district package that must be completed.

You must choose one legal city center for each role, place every required district legally, and maximize the **combined empire adjacency bonus**.

Only the tiles listed in the scenario exist.

## Output

Write your answer to:
- `/output/dual_city_plan.json`

Use this JSON structure:

```json
{
  "cities": [
    {
      "city_id": "trade_port",
      "center": [1, 1],
      "districts": {
        "HARBOR": [2, 1],
        "COMMERCIAL_HUB": [2, 2],
        "CANAL": [1, 2],
        "INDUSTRIAL_ZONE": [1, 3]
      }
    },
    {
      "city_id": "foundry_harbor",
      "center": [7, 4],
      "districts": {
        "HARBOR": [8, 4],
        "CAMPUS": [7, 3],
        "AQUEDUCT": [6, 4],
        "DAM": [7, 5],
        "INDUSTRIAL_ZONE": [6, 5]
      }
    }
  ],
  "district_adjacency": {
    "trade_port:HARBOR": 4,
    "trade_port:COMMERCIAL_HUB": 5,
    "trade_port:CANAL": 0,
    "trade_port:INDUSTRIAL_ZONE": 3,
    "foundry_harbor:HARBOR": 4,
    "foundry_harbor:CAMPUS": 3,
    "foundry_harbor:AQUEDUCT": 0,
    "foundry_harbor:DAM": 0,
    "foundry_harbor:INDUSTRIAL_ZONE": 5
  },
  "total_adjacency": 24
}
```

## Requirements

1. Output valid JSON.
2. Include exactly two city entries, one for each `city_id` from the scenario.
3. Each city center must be chosen from that role's `candidate_centers`.
4. Each city must place exactly the listed `required_districts`, with no extras.
5. All city centers and districts must obey Civ6 placement rules.
6. `district_adjacency` must contain one entry for every placed district using the key format `city_id:DISTRICT_NAME`.
7. `total_adjacency` must equal the sum of all reported district adjacency values.
8. The reported adjacency values must be accurate.

## Goal

Maximize the final `total_adjacency`.
