# Civ6 District Reserve Planner (Similar)

## Task

You are planning one fixed-city Civ6 district layout on a small hex-map slice.
The city center is already settled and cannot move.
You must place every required district and infrastructure listed in the scenario while respecting reserved tiles, district legality, the city population cap, and tile overlap constraints.
Your goal is to maximize the **total weighted adjacency score**.

## Scenario

Read:
- `/data/weighted_reserve_scenario.json`

The scenario file gives you:
- the fixed `city_center`
- the city `population`
- the required builds in `required_builds`
- per-build score multipliers in `weights`
- blocked coordinates in `reserved_tiles`
- the explicit hex tiles in `tiles`

## Rules

Use standard Civ6 district legality and adjacency behavior for these builds:
- `CAMPUS`
- `HOLY_SITE`
- `INDUSTRIAL_ZONE`
- `COMMERCIAL_HUB`
- `HARBOR`
- `AQUEDUCT`
- `DAM`

In particular:
- Every build must be within 3 tiles of the fixed city center.
- `HARBOR` must be on `COAST` or `LAKE` and adjacent to land.
- `AQUEDUCT` must be adjacent to the city center and connected to fresh water.
- `DAM` must be on floodplains crossed by a river on at least two edges.
- Reserved tiles cannot host any build, but they still exist for adjacency purposes.
- Placing a district on woods or rainforest removes that feature before final adjacency is scored.
- The city may have at most `1 + floor((population - 1) / 3)` specialty districts.

## Output

Write JSON to:
- `/output/civ6_weighted_reserve_plan.json`

Use this shape:

```json
{
  "city_center": [21, 13],
  "placements": {
    "CAMPUS": [21, 14],
    "HOLY_SITE": [23, 12],
    "INDUSTRIAL_ZONE": [22, 13],
    "COMMERCIAL_HUB": [20, 13],
    "HARBOR": [21, 12],
    "AQUEDUCT": [22, 12],
    "DAM": [23, 14]
  },
  "district_scores": {
    "CAMPUS": {"raw_adjacency": 6, "weight": 3, "weighted_score": 18},
    "HOLY_SITE": {"raw_adjacency": 2, "weight": 2, "weighted_score": 4}
  },
  "total_weighted_score": 54
}
```

## Requirements

1. `placements` must include every required build exactly once.
2. `district_scores` must include every required build exactly once.
3. Each `district_scores.<name>.weight` must match the scenario weight for that build.
4. Each `weighted_score` must equal `raw_adjacency * weight`.
5. `total_weighted_score` must equal the sum of all per-build `weighted_score` values.
6. The verifier will recompute legality, per-build adjacency, and the true optimal total weighted score.
