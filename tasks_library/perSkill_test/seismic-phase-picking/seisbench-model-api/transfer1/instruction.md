You have workload descriptions at `/root/data/compute_scenarios.csv`.

Create `/root/transfer1_throughput_tuning.csv`.

Requirements:
1. Preserve input row order.
2. Write exactly these columns: `scenario_id`, `use_gpu`, `increase_batch_size`, `compile_model`, `use_asyncio`, `manual_resampling`, `primary_bottleneck`.
3. Use these rules:
   - `use_gpu = yes` only if `gpu_available` is `yes` and `dataset_size` is `large`; else `no`
   - `increase_batch_size = yes` only if `dataset_size` is `large`; else `no`
   - `compile_model = yes` only if `torch2_available` is `yes` and `dataset_size` is `large`; else `no`
   - `use_asyncio = yes` only if `io_bound` is `yes`; else `no`
   - `manual_resampling = yes` only if `sample_rate_mismatch` is `yes`; else `no`
   - `primary_bottleneck = "io"` when `io_bound` is `yes`, otherwise `compute`
4. Do not read anything from `/tests`.
