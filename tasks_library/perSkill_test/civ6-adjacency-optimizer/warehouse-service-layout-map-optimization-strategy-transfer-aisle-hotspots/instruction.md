# Warehouse Service Layout (Transfer)

## Task

You are planning a compact warehouse service layout on a square-grid floor map.
The shelves are fixed.
You must place the required service equipment on valid service pads so that the shelves receive the highest possible total service score.

The layout must satisfy all of these constraints:
- equipment can only be placed on marked service pads
- pads on or directly orthogonally adjacent to fire aisles are unusable
- two pieces of equipment cannot occupy the same pad
- every pair of placed devices must be at least Manhattan distance `2` apart

## Scenario

Read:
- `/data/warehouse_layout_scenario.json`

The scenario gives you:
- the warehouse `layout`
- the required number of each device type in `device_counts`
- per-device scoring tables in `service_rules`
- shelf demand values in `shelves`

## Scoring

For each shelf:
- the shelf gets service from the **best single** `pick_station`
- the shelf gets service from the `charging_dock`
- the shelf gets service from the **best single** `buffer_table`

Distance is Manhattan distance on the grid.
Each device type multiplies its own demand field by the coefficient for that distance.
If a distance is missing from the device's `distance_scores`, that device contributes `0` at that distance.

The total objective is:
- the sum of all shelf totals across all shelves

## Output

Write JSON to:
- `/output/warehouse_service_layout.json`

Use this shape:

```json
{
  "placements": {
    "pick_stations": [[2, 1], [7, 1]],
    "charging_dock": [6, 3],
    "buffer_tables": [[2, 5], [5, 5]]
  },
  "shelf_service": {
    "S1": {
      "pick_station": {"coord": [2, 1], "distance": 1, "score": 45},
      "charging_dock": {"coord": null, "distance": null, "score": 0},
      "buffer_table": {"coord": null, "distance": null, "score": 0},
      "total": 45
    }
  },
  "total_service_score": 177
}
```

## Requirements

1. `placements.pick_stations` must contain exactly the required number of pick stations.
2. `placements.charging_dock` must be one coordinate pair.
3. `placements.buffer_tables` must contain exactly the required number of buffer tables.
4. Every placed coordinate must be a legal service pad after applying the fire-aisle clearance rule.
5. `shelf_service` must include every shelf exactly once.
6. Each shelf entry must report the chosen contributing device, its Manhattan distance, its score, and the shelf total.
7. `total_service_score` must equal the sum of all shelf totals.
8. The verifier will recompute legality, per-shelf service, and the true optimal total.
