You are given:
- `/root/transfer1_jobs.json`
- `/root/transfer1_template.py`

Create two files:
1. `/root/modal_jobs/transfer1/batch_jobs.py`
2. `/root/modal_jobs/transfer1/results_manifest.json`

Requirements:
1. Build one Modal function per job in `transfer1_jobs.json`.
2. Function naming rule: `run_<job_id>` with `-` replaced by `_`.
3. Each function must use `@app.function(gpu="<gpu>", image=base_image, timeout=<timeout_seconds>)`.
4. Fill template placeholders so there are no remaining `__...__` tokens.
5. Keep the local entrypoint and make it call every generated function with `.remote()`.
6. `results_manifest.json` must be a JSON array sorted by `job_id`. Each row must contain:
   - `job_id`
   - `function_name`
   - `gpu`
   - `timeout_minutes` (integer, computed as `timeout_seconds // 60`)
