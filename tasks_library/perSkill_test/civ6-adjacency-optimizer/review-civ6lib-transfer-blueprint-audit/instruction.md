# Transfer: Expansion Blueprint Audit Board

## Task

You are reviewing a small Civilization VI planning board that contains several candidate expansion blueprints.

Read the scenario file at:
- `/data/frontier_blueprint_board/scenario.json`

The file contains:
- the tile list for a fixed frontier map,
- two city roles with fixed population and required district packages,
- several candidate blueprints submitted by different planners,
- each blueprint's claimed total adjacency score.

Your job is to audit every blueprint:
1. Decide whether the proposed city centers and district placements are legal.
2. Recalculate every valid blueprint's district adjacency exactly.
3. Report why invalid blueprints fail.
4. Rank only the valid blueprints by recomputed total adjacency.
5. Identify the single best valid blueprint.

## Output

Write your report to:
- `/output/blueprint_audit.json`

Use this JSON structure:

```json
{
  "scenario_id": "frontier_blueprint_board",
  "audits": [
    {
      "blueprint_id": "ledger_peak",
      "claimed_total_adjacency": 13,
      "is_valid": true,
      "errors": [],
      "claim_matches": false,
      "district_adjacency": {
        "ridge_academy:CAMPUS": 2,
        "ridge_academy:HOLY_SITE": 2,
        "ridge_academy:COMMERCIAL_HUB": 3,
        "floodplain_foundry:AQUEDUCT": 0,
        "floodplain_foundry:DAM": 0,
        "floodplain_foundry:INDUSTRIAL_ZONE": 5
      },
      "total_adjacency": 12
    }
  ],
  "valid_ranking": [
    {
      "rank": 1,
      "blueprint_id": "ledger_peak",
      "total_adjacency": 12
    }
  ],
  "best_valid_blueprint_id": "ledger_peak",
  "best_valid_total_adjacency": 12
}
```

## Requirements

1. Output valid JSON.
2. `audits` must contain exactly one entry for every candidate blueprint in the scenario, in the same order.
3. For invalid blueprints:
   - `is_valid` must be `false`
   - `errors` must explain the failure
   - `district_adjacency` must be `{}`
   - `total_adjacency` must be `0`
   - `claim_matches` must be `false`
4. For valid blueprints:
   - `errors` must be an empty list
   - `district_adjacency` must contain one entry for every placed district, keyed as `city_id:DISTRICT_NAME`
   - `total_adjacency` must equal the sum of the reported district adjacency values
   - `claim_matches` must reflect whether the blueprint's claimed total equals your recomputed total
5. `valid_ranking` must include only valid blueprints, sorted by:
   - higher `total_adjacency` first
   - then `blueprint_id` ascending as a tiebreaker
6. `best_valid_blueprint_id` and `best_valid_total_adjacency` must match the top entry in `valid_ranking`.

## Goal

Produce a complete and accurate audit board.
