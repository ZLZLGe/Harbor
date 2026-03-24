# Similar: Saturn Aurora Consensus Frontier

## Task

Citizen-science volunteers marked candidate Saturn aurora features on a small image set. Your job is to sweep a consensus-building grid, score every configuration against expert annotations, discard weak settings, and write the final non-dominated trade-off set to `/root/aurora_frontier.csv`.

## Data

Files are in `/root/data/`:

- `citizen_aurora_marks.csv`
  - Columns: `image_id`, `observer_id`, `x_px`, `y_px`
- `expert_aurora_catalog.csv`
  - Columns: `image_id`, `x_px`, `y_px`

Each row is one point annotation in pixel coordinates.

## Hyperparameter Grid

Evaluate every combination of:

- `min_support`: `2, 3, 4, 5`
- `merge_radius`: `8, 12, 16, 20, 24`
- `latitude_scale`: `0.8, 1.0, 1.2, 1.4`

## Consensus Rule

For one image and one hyperparameter combination:

1. Take all citizen points for that `image_id`.
2. Connect two citizen points when their weighted distance is at most `merge_radius`:

   ```
   d(a, b) = sqrt((Δx)^2 + (latitude_scale * Δy)^2)
   ```

3. Treat each connected component as one candidate aurora feature.
4. Drop any component with fewer than `min_support` citizen points.
5. The consensus location of a kept component is the component-wise median of its original `x_px` and `y_px` values.

## Evaluation

For each hyperparameter combination:

1. Loop over all unique `image_id` values from `expert_aurora_catalog.csv`.
2. Build consensus locations for that image using the rule above.
3. Match consensus locations to expert points greedily using standard Euclidean distance:
   - closest pair first
   - a consensus point and an expert point can be used at most once
   - ignore candidate pairs farther than `24` pixels
4. For each image, compute:
   - `agreement_score`: F1 score from the matched counts
   - `localization_error`: mean Euclidean distance of matched pairs
5. Average `agreement_score` across all expert images.
6. Average `localization_error` only across images with at least one match.

Additional rules:

- If an expert image has no citizen points, no kept components, or no valid matches, that image contributes `agreement_score = 0.0`.
- For those same cases, that image contributes `localization_error = NaN`, and those `NaN` values are excluded from the localization average.
- Keep only configurations with `agreement_score >= 0.50` and a finite averaged `localization_error`.

## Duplicate Objective Rule

After rounding `agreement_score` and `localization_error` to 5 decimal places, multiple hyperparameter settings may land on the same objective pair. If that happens, keep only the lexicographically smallest hyperparameter tuple:

1. smaller `min_support`
2. then smaller `merge_radius`
3. then smaller `latitude_scale`

Apply this tie rule before computing the final non-dominated trade-off set.

## Output

Write `/root/aurora_frontier.csv` with exactly these columns in this order:

```csv
agreement_score,localization_error,min_support,merge_radius,latitude_scale
```

Formatting requirements:

- round `agreement_score` to 5 decimal places
- round `localization_error` to 5 decimal places
- round `latitude_scale` to 1 decimal place
- keep `min_support` and `merge_radius` as integers
- sort the final rows by `agreement_score` descending, then `localization_error` ascending, then the three hyperparameters ascending
