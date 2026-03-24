# Similar | Lunar Boulder Consensus Sweep

## Task

You are given citizen-science clicks for suspected lunar boulders and a smaller reference catalog reviewed by the science team.

Run a full DBSCAN grid search across the provided tile suite, score every parameter combination, and write the top 15 configurations to `/root/lunar_boulder_leaderboard.csv`.

## Data

Files are in `/root/data/`:

- `volunteer_boulders.csv`
  - `tile_id`
  - `observer_id`
  - `x_px`
  - `y_px`
- `reference_boulders.csv`
  - `tile_id`
  - `catalog_id`
  - `x_px`
  - `y_px`
- `tile_manifest.csv`
  - one row per tile in the evaluation suite

Use every `tile_id` listed in `tile_manifest.csv`, even if a tile has no volunteer clicks.

## Hyperparameter Grid

Evaluate every combination of:

- `eps_px`: `6, 8, 10, 12, 14, 16, 18`
- `min_samples`: `2, 3, 4, 5, 6`
- `east_west_scale`: `0.70, 0.85, 1.00, 1.15, 1.30, 1.45, 1.60`

Before clustering, multiply only the x-coordinate by `east_west_scale`. Keep the original coordinates for centroid calculation and scoring.

## Per-tile Scoring

For each parameter combination and each tile:

1. Cluster volunteer clicks with DBSCAN.
2. Ignore noise points.
3. Compute one centroid per cluster using the original `x_px` and `y_px`.
4. Match centroids to reference boulders greedily by smallest standard Euclidean distance first.
5. Discard candidate matches above `45` pixels.
6. Compute:
   - `tile_f1`
   - `tile_localization_error`: mean Euclidean distance across matched pairs

Use:

- `precision = tp / (tp + fp)`
- `recall = tp / (tp + fn)`
- `tile_f1 = 2 * precision * recall / (precision + recall)`

If a tile has no volunteer clicks, no clusters, or no valid matches, set `tile_f1 = 0.0` and treat `tile_localization_error` as missing for that tile.

## Aggregation

For each parameter combination:

- `mean_f1` is the arithmetic mean of `tile_f1` over every tile in `tile_manifest.csv`
- `mean_localization_error` is the arithmetic mean over tiles whose localization error is not missing

## Ranking And Output

Rank all parameter combinations by:

1. `mean_f1` descending
2. `mean_localization_error` ascending
3. `eps_px` ascending
4. `min_samples` ascending
5. `east_west_scale` ascending

Write only the top 15 rows to `/root/lunar_boulder_leaderboard.csv` with this exact header:

```csv
rank,mean_f1,mean_localization_error,eps_px,min_samples,east_west_scale
```

Formatting rules:

- `rank` is `1` through `15`
- round `mean_f1` and `mean_localization_error` to 6 decimal places
- round `east_west_scale` to 2 decimal places
- keep `eps_px` and `min_samples` as integers
