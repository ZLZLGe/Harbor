# Transfer: Wildfire Relay Coverage Network

## Task

Plan a wildfire drone relay network on an **odd-r hex grid**.
The base is fixed. Choose up to `max_stations` relay sites so that as much hotspot risk as possible is covered by the base-connected network.

## Scenario

Read the scenario at:
- `/data/wildfire_relay/scenario.json`

The scenario defines:
- the fixed base coordinate
- the available map tiles
- which tiles are buildable for relay stations
- the hotspot coordinates and their risk values
- the maximum number of stations
- the minimum allowed station-to-station distance
- the communication radius for relay links
- the coverage radius for the base and each connected relay

`buildable = false` tiles still exist on the map and still count for distance, link, and coverage calculations, but you cannot place a relay station on them.

Each listed station must be part of a relay chain that reaches the base using hops of at most `link_radius`.

## Output

Write a JSON object to:
- `/output/wildfire_relay_plan.json`

Required format:

```json
{
  "stations": [[2, 1], [3, 4], [5, 4], [6, 2]],
  "covered_hotspots": [[2, 5], [3, 0], [4, 5], [5, 1], [6, 1], [6, 2], [6, 4]],
  "coverage_score": 61
}
```

## Requirements

1. `stations` must contain unique coordinates and use at most `max_stations` entries.
2. Every station must be on a valid `buildable` tile and must not overlap the base.
3. Every pair of stations must be at least `min_station_distance` hexes apart.
4. The base plus all listed stations must form a connected relay network where every hop is at most `link_radius`.
5. `covered_hotspots` must contain exactly the hotspot coordinates covered by the base or a connected station within `coverage_radius`.
6. `coverage_score` must equal the sum of the risk values of `covered_hotspots`.

## Scoring

- Invalid format, invalid placement, disconnected relays, or incorrect coverage accounting = 0 points
- Valid output = `your_coverage_score / optimal_coverage_score`, capped at `1.0`
