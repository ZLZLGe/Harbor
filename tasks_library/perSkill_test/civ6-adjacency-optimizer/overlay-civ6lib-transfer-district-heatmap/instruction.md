# Transfer: District Placement Heatmap Generator

## Task

You are preparing a placement heatmap for one fixed Civilization VI city.

Read the scenario file at:
- `/data/volcanic_hinterland_heatmap/scenario.json`

The scenario gives you:
- one fixed city center,
- a fixed population,
- several already locked districts that remain in place,
- a small set of reserved tiles that must stay unused,
- a list of candidate district types that should be analyzed,
- the full tile list for this micro-map.

Your job is not to redesign the city. Instead, evaluate each candidate district independently:
1. Keep the city center and all locked districts exactly where the scenario places them.
2. For one candidate district at a time, enumerate every legal tile where that district could be built.
3. Ignore reserved tiles even if the normal game rules would allow them.
4. Recalculate the candidate district's own adjacency bonus and the city's resulting total adjacency after adding that district.
5. Produce a ranked heatmap-style report for every candidate district.

Only the listed tiles exist.

## Output

Write your report to:
- `/output/district_heatmap.json`

Use this JSON structure:

```json
{
  "scenario_id": "volcanic_hinterland_heatmap",
  "city_center": [3, 3],
  "baseline_total_adjacency": 6,
  "heatmaps": [
    {
      "district": "CAMPUS",
      "best_tile": [5, 3],
      "best_district_adjacency": 1,
      "legal_tile_count": 8,
      "ranked_tiles": [
        {
          "tile": [5, 3],
          "district_adjacency": 1,
          "empire_delta": 2,
          "resulting_total_adjacency": 8
        }
      ]
    }
  ]
}
```

## Requirements

1. Output valid JSON.
2. `scenario_id` must match the scenario file.
3. `city_center` must exactly match the fixed city center from the scenario.
4. `baseline_total_adjacency` must equal the total adjacency of the locked city before adding any candidate district.
5. `heatmaps` must contain exactly one entry for every district listed in `candidate_districts`, in the same order.
6. Each heatmap entry must include:
   - `district`
   - `best_tile`
   - `best_district_adjacency`
   - `legal_tile_count`
   - `ranked_tiles`
7. `ranked_tiles` must contain every and only legal non-reserved tiles for that district.
8. Each `ranked_tiles` entry must report:
   - the tile coordinates,
   - that candidate district's exact adjacency after placement,
   - `empire_delta`, defined as `resulting_total_adjacency - baseline_total_adjacency`,
   - the exact `resulting_total_adjacency`.
9. Within each district heatmap, sort `ranked_tiles` by:
   - higher `district_adjacency` first,
   - then higher `empire_delta`,
   - then lower `y`,
   - then lower `x`.
10. `best_tile` and `best_district_adjacency` must match the first entry in `ranked_tiles`.

## Goal

Produce a complete and accurate placement heatmap report.
