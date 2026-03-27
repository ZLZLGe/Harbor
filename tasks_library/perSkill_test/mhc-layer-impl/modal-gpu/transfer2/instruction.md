You are given `/root/deployment_matrix.csv`.

Create two files:
1. `/root/modal_jobs/transfer2/deployment_plan.md`
2. `/root/modal_jobs/transfer2/deployment_plan.json`

For each CSV row (`model_name,token_budget_m,deadline_minutes,priority`) compute:
1. `gpu_tier`:
   - `A100` if `token_budget_m >= 800` OR `deadline_minutes <= 30`
   - `A10G` if rule above is false and (`token_budget_m >= 300` OR `deadline_minutes <= 60`)
   - otherwise `T4`
2. `concurrency`:
   - `2` when priority is `critical` or `high`
   - `1` otherwise
3. `modal_command` = `modal run deploy_<model_name>.py`, where `<model_name>` is lowercase and every non-alphanumeric character is replaced by `_`.

Output rules:
1. JSON output must be an array preserving CSV row order.
2. Markdown output must contain a table with columns:
   - `model_name`
   - `gpu_tier`
   - `concurrency`
   - `modal_command`
