# Wetland Restoration Layout (Transfer)

## Task

You are planning a restoration layout for a protected wetland reserve.
Candidate sites are fixed.
You must place the required set of filter islands, observation points, and trailheads so that the reserve gets the highest combined habitat coverage score and facility synergy score.

The layout must satisfy all of these constraints:
- each facility can only use candidate sites of its own type
- filter islands cannot use sites blocked by protected navigation channels
- no selected site may fall inside a sensitive nest exclusion radius
- selected sites must respect the minimum interference radii for same-type and cross-type pairs

## Scenario

Read:
- `/data/wetland_restoration_scenario.json`

The scenario gives you:
- the required number of each facility in `required_counts`
- typed candidate sites in `candidate_sites`
- habitat hotspots in `habitat_clusters`
- nest exclusion zones in `sensitive_nests`
- coverage radii in `coverage_radii`
- interference radii in `interference_radii`
- pairwise link bonuses in `synergy_rules`

## Scoring

For each habitat cluster:
- add its `filter_island` score if at least one chosen filter island is within the filter coverage radius
- add its `observation_point` score if at least one chosen observation point is within the observation coverage radius
- add its `trailhead` score if at least one chosen trailhead is within the trailhead coverage radius
- add its `restoration_bonus` if the cluster is covered by both a filter island and an observation point

Facility synergy is scored separately:
- each chosen filter island and chosen observation point pair earns the `filter_observation` bonus when their site distance is within that rule's radius
- each chosen observation point and chosen trailhead pair earns the `observation_trailhead` bonus when their site distance is within that rule's radius

The total objective is:
- `sum(cluster coverage scores) + total facility synergy score`

## Output

Write JSON to:
- `/output/wetland_restoration_layout.json`

Use this shape:

```json
{
  "placements": {
    "filter_islands": ["F2", "F5"],
    "observation_points": ["O1", "O3"],
    "trailheads": ["T1", "T3"]
  },
  "cluster_scores": {
    "H1": {
      "covered_by": {
        "filter_islands": ["F2"],
        "observation_points": ["O1"],
        "trailheads": ["T1"]
      },
      "component_scores": {
        "filter_island": 16,
        "observation_point": 7,
        "trailhead": 4,
        "restoration_bonus": 5
      },
      "coverage_score": 32
    }
  },
  "facility_synergy": {
    "filter_observation_links": [
      {"filter_island": "F5", "observation_point": "O3", "score": 3}
    ],
    "observation_trailhead_links": [
      {"observation_point": "O1", "trailhead": "T1", "score": 4}
    ],
    "total_synergy_score": 7
  },
  "total_score": 39
}
```

## Requirements

1. `placements.filter_islands`, `placements.observation_points`, and `placements.trailheads` must contain exactly the required number of site IDs.
2. Every reported site ID must exist in the scenario under the correct facility type.
3. All chosen sites must satisfy the blocked-waterway, nest exclusion, and interference-radius rules.
4. `cluster_scores` must include every habitat cluster exactly once.
5. Each cluster entry must report the exact covering site IDs, component scores, and `coverage_score`.
6. `facility_synergy` must report every scoring filter-observation link and observation-trailhead link exactly once.
7. `total_synergy_score` must equal the sum of all reported link scores.
8. `total_score` must equal the sum of all cluster `coverage_score` values plus `total_synergy_score`.
9. The verifier will recompute legality, coverage, synergy, and the true optimal total.
