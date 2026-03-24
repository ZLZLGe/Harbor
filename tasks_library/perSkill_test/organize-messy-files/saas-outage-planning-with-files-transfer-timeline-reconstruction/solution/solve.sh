#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
INCIDENT_ROOT="${INCIDENT_ROOT:-$TASK_ROOT/incident_workspace}"
REPORT_DIR="$TASK_ROOT/reports"
REPORT_PATH="$REPORT_DIR/outage_postmortem.md"

mkdir -p "$REPORT_DIR"

cat > "$TASK_ROOT/task_plan.md" <<EOF
# Task Plan

## Goal
Reconstruct the checkout outage timeline from the incident workspace and write \`reports/outage_postmortem.md\`.

## Phases
- [x] Review alerts, logs, chat notes, tickets, and config snapshots in \`$INCIDENT_ROOT\`.
- [x] Build a UTC timeline from deployment through recovery.
- [x] Compare competing leads and settle on the most likely root cause.
- [x] Write the final report and save progress notes.

## Key checkpoints
- Confirm the trigger around release \`2026.02.14-rc3\`.
- Separate primary cause from the later payments provider warning.
- Capture outage window and mitigation timing.
EOF

cat > "$TASK_ROOT/findings.md" <<EOF
# Findings

- \`tickets/CHG-771.md\` shows release \`2026.02.14-rc3\` finished at 09:12:18 UTC and skipped production flag validation.
- \`config/checkout.after.env\` set \`INVOICE_PREFETCH_MODE=sync\` after \`config/checkout.before.env\` had \`INVOICE_PREFETCH_MODE=off\`, while \`PGPOOL_MAX_CONN=48\` stayed unchanged.
- \`logs/checkout-api.log\` and \`logs/postgres_pool.log\` show checkout requests failing with db pool exhaustion and connection acquire timeouts starting just after the deployment.
- \`alerts/alerts_export.csv\` shows \`DBPoolSaturation\`, checkout latency, and 5xx alerts firing before the provider latency warning.
- \`chat/oncall_chat.md\` records that disabling invoice prefetch at 09:31 UTC immediately reduced 5xx rate and pool waiters.
- \`tickets/INC-4821.md\` states that 23% of checkout attempts failed between 09:16 UTC and 09:39 UTC.
EOF

cat > "$TASK_ROOT/progress.md" <<EOF
# Progress

- Reviewed all evidence files under \`$INCIDENT_ROOT\`.
- Correlated deployment time, alert start, pool saturation, incident declaration, mitigation, and recovery.
- Wrote \`$REPORT_PATH\` with a timeline table, root cause hypothesis, key evidence, and open questions.
EOF

cat > "$REPORT_PATH" <<'EOF'
# Outage Postmortem

## Executive Summary
On 2026-02-14, checkout traffic degraded minutes after `checkout-api` release `2026.02.14-rc3` reached production. The strongest evidence points to the newly enabled synchronous invoice prefetch path exhausting the service's PostgreSQL connection pool, which caused checkout latency and 5xx failures. The later payments provider warning appears secondary because it started after the internal pool and checkout alerts.

## Customer Impact
The affected surface was `/v1/checkout/session`, which drove web and mobile checkout. Based on `tickets/INC-4821.md`, about 23% of checkout attempts failed between 2026-02-14 09:16 UTC and 2026-02-14 09:39 UTC, while cart view and login remained unaffected.

## Timeline
| Time (UTC) | Event | Evidence |
| --- | --- | --- |
| 2026-02-14 09:12:18 | `checkout-api` release `2026.02.14-rc3` completed in production. | `tickets/CHG-771.md`, `logs/checkout-api.log` |
| 2026-02-14 09:13:02 | The service loaded `INVOICE_PREFETCH_MODE=sync`, changing checkout behavior immediately after deploy. | `logs/checkout-api.log`, `config/checkout.after.env`, `config/checkout.before.env` |
| 2026-02-14 09:14:55 | Checkout latency alert began firing on `/v1/checkout/session`. | `alerts/alerts_export.csv` |
| 2026-02-14 09:16:10 | First logged checkout failures reported `db pool exhausted`, matching the outage start window in the incident ticket. | `logs/checkout-api.log`, `tickets/INC-4821.md` |
| 2026-02-14 09:18:07 | DB pool saturation alert and pool timeout errors confirmed connection exhaustion inside `checkout-api`. | `alerts/alerts_export.csv`, `logs/postgres_pool.log` |
| 2026-02-14 09:20:11 | Payments provider latency warning appeared after the internal pool alerts, making it a weaker primary-cause candidate. | `alerts/alerts_export.csv`, `chat/oncall_chat.md` |
| 2026-02-14 09:26:40 | The team declared SEV-1 as checkout failures spread across web and mobile checkout. | `tickets/INC-4821.md`, `chat/oncall_chat.md` |
| 2026-02-14 09:31:02 | On-call disabled invoice prefetch in production. | `logs/checkout-api.log`, `chat/oncall_chat.md` |
| 2026-02-14 09:34:48 | DB pool saturation resolved and operators observed waiters dropping immediately after the flag change. | `alerts/alerts_export.csv`, `chat/oncall_chat.md`, `logs/postgres_pool.log` |
| 2026-02-14 09:39:12 | Latency alert resolved, marking practical recovery of checkout traffic. | `alerts/alerts_export.csv`, `tickets/INC-4821.md` |

## Root Cause Hypothesis
The most likely trigger was release `2026.02.14-rc3` enabling `INVOICE_PREFETCH_MODE=sync` in production without validating the flag state during rollout. That change added synchronous invoice prefetch work to the checkout request path, and the logs show those queries holding PostgreSQL connections for roughly 7 to 8 seconds. Because `PGPOOL_MAX_CONN` stayed at 48, the extra synchronous work exhausted the PostgreSQL connection pool, leading to `db pool exhausted` and `timeout waiting for idle postgres connection` failures. The payments provider warning is less plausible as the primary cause because it fired later and the chat notes say the provider degraded only after backlog growth.

## Key Evidence
- `config/checkout.before.env` and `config/checkout.after.env` show the decisive runtime change: `INVOICE_PREFETCH_MODE` moved from `off` to `sync` while pool sizing remained unchanged.
- `tickets/CHG-771.md` records that release `2026.02.14-rc3` finished at 09:12:18 UTC and skipped the production flag validation step.
- `logs/checkout-api.log` ties the new sync prefetch mode to checkout failures, including `db pool exhausted` and idle connection timeout errors.
- `logs/postgres_pool.log` shows the pool pegged at 48 in-use connections with dozens of waiters before mitigation and healthy idle capacity after mitigation.
- `alerts/alerts_export.csv` places the DB pool and checkout alerts ahead of the payments provider warning and shows recovery after the feature flag was disabled.
- `chat/oncall_chat.md` confirms that disabling invoice prefetch at 09:31 UTC immediately reduced 5xx rate and pool waiters.

## Open Questions
- Why did the synchronous invoice prefetch query hold PostgreSQL connections for more than 7 seconds under normal checkout load?
- Why was the production flag validation step skipped in `CHG-771`, and why did the canary path fail to catch the config difference?
- Should `checkout-api` keep invoice prefetch off by default until pool sizing, query performance, and rollout validation are tightened?
EOF
