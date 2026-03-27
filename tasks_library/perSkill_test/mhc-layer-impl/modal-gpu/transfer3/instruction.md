You are given `/root/failure_events.json`.

Create two files:
1. `/root/modal_jobs/transfer3/recovery_playbook.json`
2. `/root/modal_jobs/transfer3/retry_modal.py`

For each event row, compute `next_attempt = attempts + 1` and apply these rules:
1. `timeout`:
   - `recommended_gpu` stays unchanged
   - `action` = `increase-timeout`
   - `retry_delay_seconds` = 60
2. `oom`:
   - upgrade GPU by one tier (`T4 -> A10G -> A100`, `A100` stays `A100`)
   - `action` = `shrink-batch-upgrade-gpu`
   - `retry_delay_seconds` = 30
3. `network`:
   - keep GPU unchanged
   - `action` = `retry-network`
   - `retry_delay_seconds` = 120
4. `quota`:
   - downgrade GPU by one tier (`A100 -> A10G -> T4`, `T4` stays `T4`)
   - `action` = `offpeak-fallback`
   - `retry_delay_seconds` = 300

`recovery_playbook.json` must be an array preserving input order and include exactly these keys per row:
- `run_id`
- `next_attempt`
- `recommended_gpu`
- `action`
- `retry_delay_seconds`

`retry_modal.py` must be valid Python and include:
- `import modal`
- `app = modal.App("mhc-transfer-recovery")`
- a function named `select_retry_config(event)` implementing the same rule logic
- at least one `@app.function(...)`-decorated function that uses `select_retry_config`
