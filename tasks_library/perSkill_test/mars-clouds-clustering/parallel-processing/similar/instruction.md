# Similar - Mars Sweep Frontier

You are given one dataset at `/root/data/scenes.json`.

Evaluate the full hyperparameter grid:
- `min_samples`: 3, 4, 5, 6
- `epsilon`: 4, 8, 12, 16
- `shape_weight`: 0.9, 1.1, 1.3, 1.5

For each combination, compute per-scene `F1` and `delta` using the deterministic scoring rules implied by the dataset schema, then compute the mean values across all scenes.

Keep only combinations with mean `F1 > 0.58`.

From the kept rows, output the Pareto frontier for:
- maximize `F1`
- minimize `delta`

Write exactly one CSV file:
- `/outputs/similar_frontier.csv`

The CSV must contain this header in this order:
- `F1,delta,min_samples,epsilon,shape_weight`

Formatting rules:
- round `F1` and `delta` to 5 decimal places
- round `shape_weight` to 1 decimal place
- sort rows by `F1` descending, then `delta` ascending
