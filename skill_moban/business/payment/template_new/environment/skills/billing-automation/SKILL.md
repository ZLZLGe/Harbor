---
name: billing-automation
description: Normalize the local billing batch inputs, compute licensed and metered billables, apply current-cycle adjustments, and route one action per subscription before replaying the batch processor.
---

# Billing Automation

Use this skill when a task asks you to build or complete a local renewal, invoicing, or collections batch from task-local data and starter code.

## What This Skill Is Good For

- Reading plan catalogs, subscription snapshots, invoice snapshots, usage rows, and policy files as one batch.
- Separating recurring licensed charges from metered usage charges.
- Applying current-cycle seat or plan changes with remaining-period proration.
- Distinguishing manual-invoice, retry, missing-payment-method, exhausted-collection, and monitor cases.
- Replaying the local batch processor and checking that batch totals stay aligned with row-level outputs.

## Recommended Workflow

1. Read `/root/data/billing_manifest.json`, `/root/data/billing_policy.yaml`, and `/root/data/plan_catalog_seed.json`.
2. Normalize prices by `price_id` and group usage and change requests by `subscription_id`.
3. For each subscription in the manifest batch scope:
   - resolve the licensed renewal target from the latest approved change effective on or before the renewal date;
   - compute the renewal amount as licensed recurring charges plus metered usage charges for the current run;
   - compute the current-cycle adjustment from the recurring delta multiplied by the remaining-period fraction;
   - compute tax from the taxable subtotal and the policy tax rate;
   - compute outstanding amount from the latest invoice snapshot.
4. Route actions with this priority:
   - `send_manual_invoice` for manual-invoice subscriptions that need the current batch or already carry an outstanding balance;
   - `pause_entitlement` when automatic collection is already exhausted under the policy thresholds;
   - `collect_payment_method` when automatic collection is blocked by a missing usable payment method;
   - `retry_payment` when automatic collection has a scheduled retry within the allowed retry range;
   - `monitor` when the subscription is still upcoming and has no outstanding balance;
   - `charge_renewal` otherwise.
5. Re-run `/root/app/main.py` after edits and check that shadow changes in usage or approved quantity changes alter the outputs in the expected direction.

## Helper Scripts

- `python3 /root/.codex/skills/billing-automation/scripts/batch_audit.py`
  - Prints one normalized audit record per in-scope subscription.
- `python3 /root/.codex/skills/billing-automation/scripts/inspect_subscription.py SUB-1007`
  - Shows the subscription, invoice, usage, change, computed amounts, and suggested action for one subscription.

## Notes

- `renewal_amount_due` includes licensed recurring charges plus metered billables.
- `adjustment_amount` covers only current-cycle approved changes.
- Manual-invoice routing stays ahead of charge collection.
- Exhausted collection stays ahead of missing-payment-method collection.
