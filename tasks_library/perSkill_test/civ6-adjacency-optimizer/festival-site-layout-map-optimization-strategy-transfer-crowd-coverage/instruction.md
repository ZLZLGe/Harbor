# Festival Site Layout (Transfer)

## Task

You are planning a compact outdoor music festival site.
Candidate pads for each facility type are fixed.
You must place the required stages, supply stations, first-aid points, and power nodes so that the site achieves the highest total score from crowd-zone coverage and powered-facility bonuses.

The layout must satisfy all of these constraints:
- each facility can only use candidate sites of its own type
- stage sites inside any quiet-zone noise buffer are illegal
- sites listed under `restricted_sites` are unusable
- selected facilities must satisfy the minimum spacing rules for same-type and cross-type pairs

## Scenario

Read:
- `/data/festival_site_scenario.json`

The scenario gives you:
- the venue `site_map`
- required facility counts in `required_counts`
- typed candidate pads in `candidate_sites`
- quiet camping buffers in `quiet_zones`
- explicitly unusable pads in `restricted_sites`
- crowd hotspots in `crowd_zones`
- service radii in `service_radii`
- coverage coefficients in `coverage_scores`
- power-link radii and bonuses in `power_rules`
- spacing limits in `spacing_rules`

Use Euclidean distance for every radius or spacing check.

## Scoring

For each crowd zone:
- add the stage score if at least one chosen stage is within the stage service radius
- add the supply score if at least one chosen supply station is within the supply service radius
- add the first-aid score if at least one chosen first-aid point is within the first-aid service radius
- add the dual-service bonus if the zone is covered by both a supply station and a first-aid point

Power bonuses are scored separately:
- each chosen stage gets the stage power bonus if at least one chosen power node is within the stage power radius
- each chosen supply station gets the supply power bonus if at least one chosen power node is within the supply power radius
- when a facility is powered by multiple selected power nodes, report only the nearest one; break exact distance ties by lexicographically smaller power-node ID

The total objective is:
- `sum(all zone totals) + total_power_bonus`

## Output

Write JSON to:
- `/output/festival_site_plan.json`

Use this shape:

```json
{
  "placements": {
    "stages": [
      {"site_id": "ST2", "coord": [5, 2]},
      {"site_id": "ST4", "coord": [3, 5]}
    ],
    "supply_stations": [
      {"site_id": "SU1", "coord": [1, 4]},
      {"site_id": "SU3", "coord": [6, 4]}
    ],
    "first_aid_points": [
      {"site_id": "MD2", "coord": [6, 7]}
    ],
    "power_nodes": [
      {"site_id": "PW1", "coord": [1, 1]},
      {"site_id": "PW3", "coord": [7, 1]}
    ]
  },
  "zone_coverage": {
    "Z1": {
      "covered_by": {
        "stages": ["ST4"],
        "supply_stations": ["SU1"],
        "first_aid_points": []
      },
      "component_scores": {
        "stage": 12,
        "supply": 21,
        "first_aid": 0,
        "dual_service_bonus": 0
      },
      "zone_total": 33
    }
  },
  "power_links": {
    "stage_links": [
      {"stage": "ST2", "power_node": "PW3", "score": 12}
    ],
    "supply_links": [
      {"supply_station": "SU1", "power_node": "PW1", "score": 6}
    ],
    "total_power_bonus": 18
  },
  "score_summary": {
    "coverage_score": 146,
    "power_bonus": 18,
    "total_score": 164
  }
}
```

## Requirements

1. Every placement list must contain exactly the required number of facilities.
2. Each reported `site_id` must exist under the correct facility type, and each reported `coord` must exactly match the scenario coordinate for that site.
3. All chosen sites must satisfy the quiet-zone, restricted-site, and spacing rules.
4. `zone_coverage` must include every crowd zone exactly once.
5. Each zone entry must report the exact covering site IDs, component scores, and `zone_total`.
6. `power_links` must report every powered stage and powered supply station exactly once, using the nearest selected power node under the stated tie-break rule.
7. `score_summary.coverage_score` must equal the sum of all zone totals.
8. `score_summary.power_bonus` must equal `power_links.total_power_bonus`.
9. `score_summary.total_score` must equal `coverage_score + power_bonus`.
10. The verifier will recompute legality, coverage, power links, and the true optimal total.
