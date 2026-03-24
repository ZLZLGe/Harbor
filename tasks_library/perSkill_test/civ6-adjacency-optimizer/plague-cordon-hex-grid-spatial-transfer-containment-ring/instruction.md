# Transfer: Plague Containment Ring

## Task

An outbreak starts from fixed source tiles and spreads one hex edge per turn on an **odd-r hex grid**.
Choose which isolation towers to build and which corridor tiles to seal with block nodes so that the outbreak never reaches any breach tile and is fully contained by the deadline at the **minimum total cost**.

## Scenario

Read the scenario at:
- `/data/containment_ring/scenario.json`

The scenario defines:
- all passable tiles on the corridor map
- the outbreak source tiles
- the breach tiles that must stay uninfected
- the containment deadline in turns
- the available isolation tower sites, with each tower's cost, activation turn, and radius
- the available block-node sites and their costs

Any coordinate not listed in `tiles` is outside the playable map and cannot be infected or used.

## Spread Rules

1. The source tiles are infected at turn `0`.
2. On each turn `t`, every tower with `activation_turn <= t` is active before spreading is evaluated.
3. Infection then spreads from the tiles infected on the previous turn to every edge-adjacent tile that:
   - is listed in `tiles`
   - has not been infected already
   - is not sealed by a selected block node
   - is not within the radius of any active tower
4. Containment succeeds only if:
   - no breach tile is ever infected through turn `time_limit`
   - after simulating one extra turn with the same defenses, the infection produces no new tiles

## Output

Write a JSON object to:
- `/output/containment_ring.json`

Required format:

```json
{
  "isolation_towers": [[6, 2]],
  "block_nodes": [[3, 3], [4, 5]],
  "total_cost": 11,
  "last_spread_turn": 2
}
```

## Requirements

1. `isolation_towers` must contain unique coordinates chosen only from `tower_candidates`.
2. `block_nodes` must contain unique coordinates chosen only from `block_candidates`.
3. A coordinate cannot appear in both lists.
4. `total_cost` must equal the sum of the selected tower and block-node costs.
5. `last_spread_turn` must equal the final turn index on which at least one new tile became infected, or `0` if infection never expanded beyond the source.
6. The selected plan must satisfy the containment rules above.

## Scoring

- Invalid format, illegal placements, incorrect accounting, or failed containment = `0`
- Valid output = `optimal_total_cost / your_total_cost`, capped at `1.0`
