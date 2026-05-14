You need to complete the renewal batch processor for the next billing run.

The codebase under `/root/app/` already contains the batch entrypoint, data loaders, and output writers, but the billing calculation and action-routing logic is incomplete.

Input data is available in `/root/data/`:

- `billing_manifest.json`: workspace id, run date, currency rules, and batch scope.
- `plan_catalog_seed.json`: product, recurring price, and add-on catalog data.
- `subscription_snapshot.ndjson`: subscription and customer snapshots for the current batch scope.
- `invoice_snapshot.ndjson`: current open, paid, draft, and failed invoice snapshots.
- `change_requests.csv`: plan and quantity changes that must be reflected in this run when the policy requires it.
- `usage_rollups.csv`: current billing-period usage totals for metered items.
- `billing_policy.yaml`: routing, retry, pause, and tax rules for the batch.

Your task

1. Complete the billing logic in `/root/app/` so the renewal batch can process every in-scope subscription.
2. For each in-scope subscription, calculate the renewal amount, adjustment amount, tax amount, and outstanding amount for this run.
3. Assign exactly one billing action to each in-scope subscription according to the policy rules.
4. Write the final batch outputs to `/root/output/`.

Output

Create `/root/output/` if it does not exist.

1. Write `/root/output/billing_actions.csv`

The CSV columns must be exactly:

```csv
subscription_id,customer_id,currency,current_status,collection_method,latest_invoice_id,renewal_amount_due,adjustment_amount,tax_amount,outstanding_amount,action_bucket,action_reason,next_step,evidence
```

Requirements:

- Include exactly one row for every in-scope subscription.
- `renewal_amount_due`, `adjustment_amount`, `tax_amount`, and `outstanding_amount` must use decimal notation with two fractional digits.
- `renewal_amount_due` must include the current run's recurring licensed charges plus any metered billables for this batch.
- `action_bucket` must be one of:
  - `charge_renewal`
  - `send_manual_invoice`
  - `retry_payment`
  - `collect_payment_method`
  - `pause_entitlement`
  - `monitor`
- `action_reason` must be one of:
  - `renewal_ready`
  - `manual_collection_required`
  - `retry_window_open`
  - `payment_method_missing`
  - `collection_exhausted`
  - `upcoming_only`
- `next_step` must be a short operational instruction.
- `evidence` must be valid JSON stored in a single CSV field and must include enough record identifiers for audit review.

2. Write `/root/output/billing_run_summary.json`

The JSON object must include:

- `workspace_id`
- `run_date`
- `totals`
- `action_counts`
- `blocked_subscription_ids`
- `notes`

Requirements:

- `workspace_id` and `run_date` must match the task input.
- `totals.subscriptions_reviewed` must equal the number of CSV rows.
- `totals.subscriptions_needing_action` must equal the number of rows where `action_bucket` is not `monitor`.
- `totals.total_renewal_amount_due` must equal the sum of `renewal_amount_due` across the CSV.
- `totals.total_outstanding_amount` must equal the sum of `outstanding_amount` across the CSV.
- `action_counts` must include all 6 action buckets even when the count is `0`.
- `blocked_subscription_ids` must include only subscriptions that cannot move forward in this batch and must be sorted in ascending order.
- `notes` must contain at least 2 short business notes.

Notes:

- Keep the batch scoped to the subscriptions included in the provided input data.
- Requests in `change_requests.csv` that are marked to affect the current run must be reflected in the current batch when the policy requires an adjustment.
- Metered items must use the provided usage totals for the current billing period.
- Billing actions must be derived from the policy file together with the current subscription, invoice, usage, and change records.
- Do not modify files under `/root/data/`.
- Do not modify tests, verifier files, task metadata, or any skill files.
- Do not hardcode final outputs or bypass the requested batch processing logic.
- You may add helper code under `/root/app/`, but the required deliverables are the two files under `/root/output/`.
