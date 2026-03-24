# Payments Ledger Cutover Plan

## Preconditions

- `billing-worker` must be paused before any schema change.
- Capture a named snapshot: `release_cutover_pre_20260408`.
- Queue drain target before pause: fewer than `50` pending checkout jobs.

## Migration Step

Run `2026_04_08_add_cutover_columns.sql` after the snapshot completes.

Success criteria:

- `failed_batches=0`
- `ledger_backfill_lag < 500`
- runtime stays under `8 minutes`

If the migration exceeds 8 minutes or any failed batch appears, stop the cutover and prepare rollback.
