# Launch Monitoring Thresholds

- Queue drain target before migration: `pending_checkout_jobs < 50`
- Reopen gate: `error_rate < 1.5%` and `p95_checkout < 900ms`
- Rollback threshold after deploy: `error_rate > 3%` for `5 minutes`
- Rollback threshold during migration: any `failed_batches > 0`
- Rollback threshold during smoke tests: recurrence of `RL-219` or `RL-244` symptoms
