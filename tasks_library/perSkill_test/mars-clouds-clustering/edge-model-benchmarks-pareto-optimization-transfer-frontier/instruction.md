# Transfer: Edge Vision Benchmark Frontier

## Task

An embedded vision team ran validation sweeps and device benchmarks for several deployment candidates. Aggregate the logs, keep only viable configurations, and write the final non-dominated accuracy/latency trade-offs to `/root/edge_model_frontier.csv`.

## Data

Files are in `/root/data/`:

- `validation_runs.csv`
  - Columns: `config_id`, `model_name`, `runtime`, `precision`, `input_resolution`, `dataset`, `attempt`, `status`, `top1_accuracy`
- `latency_runs.jsonl`
  - One JSON object per line with fields: `config_id`, `device`, `power_mode`, `batch_size`, `phase`, `trial`, `status`, `warmup`, `latency_ms`

`config_id` is the join key between the two files. The tuple `(model_name, runtime, precision, input_resolution)` is the human-readable configuration identity and is consistent within each `config_id`.

## Validation Aggregation

Required validation datasets:

- `road_signs`
- `shelf_labels`
- `fruit_sorting`

For each configuration:

1. Keep only validation rows where `status == "ok"`.
2. For each required dataset, take the maximum `top1_accuracy` across successful attempts.
3. Discard the configuration if any required dataset is missing after step 1.
4. Compute `validation_accuracy` as the arithmetic mean of the three per-dataset maxima.
5. Keep only configurations with `validation_accuracy >= 0.9000`.

## Latency Aggregation

Use only latency samples that match the deployment profile below:

- `device == "orin-nano"`
- `power_mode == "15W"`
- `batch_size == 1`
- `phase == "timed"`
- `status == "ok"`
- `warmup == false`

For each configuration:

1. Discard it unless at least 3 matching timed trials remain.
2. Compute `mean_latency_ms` as the arithmetic mean of the matching `latency_ms` values.

## Frontier

Join the surviving validation summary with the surviving latency summary on `config_id`.

From that joined table, compute the Pareto frontier with these objectives:

- maximize `validation_accuracy`
- minimize `mean_latency_ms`

Use the aggregated numeric values before rounding when deciding Pareto optimality.

## Output

Write `/root/edge_model_frontier.csv` with exactly these columns in this order:

```csv
validation_accuracy,mean_latency_ms,model_name,runtime,precision,input_resolution
```

Formatting requirements:

- round `validation_accuracy` to 4 decimal places
- round `mean_latency_ms` to 2 decimal places
- keep `input_resolution` as an integer
- sort the final rows by `validation_accuracy` descending, then `mean_latency_ms` ascending, then `model_name`, `runtime`, `precision`, and `input_resolution` ascending
