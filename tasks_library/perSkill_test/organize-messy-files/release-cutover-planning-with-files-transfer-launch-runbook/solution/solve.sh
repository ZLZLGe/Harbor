#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
RELEASE_WORKSPACE="${RELEASE_WORKSPACE:-$TASK_ROOT/release_workspace}"

mkdir -p "$TASK_ROOT/plans"

cat > "$TASK_ROOT/task_plan.md" <<'EOF'
# Task Plan

1. Read the release scope, owner roster, and go/no-go notes to lock the cutover sequence and named owners.
2. Extract the migration preconditions, monitoring thresholds, and targeted defect checks that must become dependencies or rollback triggers.
3. Draft the runbook table, then add validation gates and finalize the reopen or rollback conditions.

Key watch items: T-10 migration guardrails, RL-219 validation after flag enablement, RL-244 refund lookup check, and the error_rate > 3% rollback threshold.
EOF

cat > "$TASK_ROOT/findings.md" <<'EOF'
# Findings

- Release `2026.04.08-rc2` has a maintenance window of `2026-04-08 21:00-22:15 UTC`.
- Named owners are Mara Singh, Devon Hale, Priya Natarajan, Linh Tran, and Omar Ruiz.
- Migration success requires `failed_batches=0`, `ledger_backfill_lag < 500`, and runtime under 8 minutes.
- Reopen requires `error_rate < 1.5%` and `p95_checkout < 900ms`; rollback is required if `error_rate > 3%` for 5 minutes.
- RL-219 and RL-244 are the targeted release risks that must be rechecked during smoke validation.
EOF

cat > "$TASK_ROOT/progress.md" <<'EOF'
# Progress

- Reviewed all release evidence files under `/root/release_workspace`.
- Mapped approved sequence, owners, validation checks, and rollback conditions into a single launch-day table.
- Wrote `plans/cutover_runbook.md` and cross-checked that each execution row cites evidence files.
EOF

cat > "$TASK_ROOT/plans/cutover_runbook.md" <<'EOF'
# Release Cutover Runbook

## Release Summary

Release `2026.04.08-rc2` is scheduled for the `2026-04-08 21:00-22:15 UTC` maintenance window. The in-scope services are `checkout-api`, `customer-portal`, and `billing-worker`. The cutover activates the `ledger_dual_write` and `express_wallet` feature flags after the application deploy is healthy.

## Owner Map

- Mara Singh: release manager, bridge lead, go/no-go owner, and reopen decision maker.
- Devon Hale: maintenance banner owner and queue-drain lead.
- Priya Natarajan: `billing-worker` pause, snapshot, and migration owner.
- Linh Tran: application deployment and feature-flag activation owner.
- Omar Ruiz: launch-day smoke validation owner and QA sign-off lead.

## Execution Sequence

| Step | Window | Owner | Dependencies | Action | Verification | Rollback Trigger | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | T-30 | Mara Singh | `CHG-902` approved; no open P0; no open blocking P1 | Confirm go/no-go, freeze deploys, and open the cutover bridge | Approval confirmed and blocker review complete | Abort the release if approval or blocker clearance is missing | `meetings/go_no_go_notes.md`; `qa/defect_register.csv`; `product/release_scope.md` |
| 2 | T-20 | Devon Hale | Step 1 complete | Enable the maintenance banner and drain checkout traffic below 50 pending jobs | Banner is live and `pending_checkout_jobs < 50` | Stay in pre-cutover state if the banner is not live or the queue will not drain | `product/release_scope.md`; `operations/monitoring_thresholds.md` |
| 3 | T-15 | Priya Natarajan | Queue drained and banner live | Pause `billing-worker` and capture snapshot `release_cutover_pre_20260408` | `worker_paused=true` and snapshot recorded successfully | Do not run the migration until both the pause and snapshot succeed | `migration/cutover_plan.md`; `meetings/go_no_go_notes.md` |
| 4 | T-10 | Priya Natarajan | Step 3 complete | Run `2026_04_08_add_cutover_columns.sql` | `failed_batches=0`, `ledger_backfill_lag < 500`, and runtime under 8 minutes | Roll back if migration runtime exceeds 8 minutes or any `failed_batches > 0` appears | `migration/cutover_plan.md`; `operations/monitoring_thresholds.md` |
| 5 | T-05 | Linh Tran | Migration verified | Deploy `checkout-api` and `customer-portal` version `2026.04.08-rc2` | Health checks stay green for both services | Revert the application deploy if either service stays unhealthy for 5 minutes | `product/release_scope.md`; `meetings/go_no_go_notes.md` |
| 6 | T+05 | Linh Tran | Step 5 healthy | Enable `ledger_dual_write` and `express_wallet` in production | Both flags show enabled and config propagation completes | Disable both flags if guest checkout regresses after activation | `product/release_scope.md`; `qa/defect_register.csv` |
| 7 | T+10 | Omar Ruiz | Flags enabled and config propagated | Run `guest_checkout`, `saved_card_checkout`, `refund_lookup`, and `invoice_download` smoke tests | All release-critical checks pass without RL-219 or RL-244 symptoms | Roll back if RL-219 or RL-244 symptoms recur during smoke validation | `validation/smoke_matrix.csv`; `qa/defect_register.csv` |
| 8 | T+20 | Mara Singh | Smoke tests pass; `error_rate < 1.5%`; `p95_checkout < 900ms` | Send the reopen notice, restore customer traffic, and monitor the bridge for 15 minutes before closure | Traffic is restored and no Sev-1 issue is opened during the observation window | Re-enter maintenance mode if `error_rate > 3%` for 5 minutes after reopen | `operations/monitoring_thresholds.md`; `meetings/go_no_go_notes.md` |

## Validation Gates

- `guest_checkout`: confirm guest checkout succeeds after `express_wallet` activation.
- `saved_card_checkout`: confirm returning-user checkout succeeds with saved cards.
- `refund_lookup`: confirm refund lookup returns within threshold after the migration.
- `invoice_download`: confirm invoice PDF download succeeds on the new release.

## Rollback Triggers

- Stop the cutover if `CHG-902` approval or blocker clearance is missing before the maintenance window begins.
- Roll back if the migration exceeds 8 minutes or any `failed_batches > 0` appears.
- Disable both feature flags and prepare application rollback if guest checkout regresses after flag activation.
- Roll back if RL-219 or RL-244 symptoms recur during smoke validation.
- Re-enter maintenance mode if `error_rate > 3%` for 5 minutes after reopen.
EOF

test -d "$RELEASE_WORKSPACE"
