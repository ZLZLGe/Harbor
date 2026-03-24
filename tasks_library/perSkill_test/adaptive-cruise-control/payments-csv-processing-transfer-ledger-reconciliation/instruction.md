You are reconciling a small payment ledger against a refund ledger after a weekly finance close.

Input files available in `/root`:
- `payments_ledger.csv`
- `refund_ledger.csv`

Create `reconcile_ledgers.py` and run it. The script must read both CSV files and produce:
- `reconciliation_exceptions.csv`
- `reconciliation_summary.json`

Do not modify the input files.

`payments_ledger.csv` columns:
- `payment_id`
- `order_id`
- `posted_at`
- `payment_status`
- `payment_method`
- `attempt_seq`
- `intended_order_amount`
- `charged_amount`
- `currency`
- `customer_region`

`refund_ledger.csv` columns:
- `refund_id`
- `order_id`
- `requested_at`
- `refund_status`
- `refund_reason`
- `refund_amount`
- `linked_payment_id`

Use these fixed reconciliation rules:
- Sort payment rows by `order_id`, then `posted_at`, then `payment_id`
- Sort refund rows by `order_id`, then `requested_at`, then `refund_id`
- Process every distinct `order_id` that appears in either input file
- Only `payment_status = settled` contributes to payment totals
- Only `refund_status = completed` contributes to `completed_refund_total`
- Only `refund_status = pending` contributes to `open_refund_total`
- `expected_net_amount` is the first `intended_order_amount` for that order after the required payment sort
- `actual_net_amount = settled_payment_total - completed_refund_total`
- `duplicate_charge_amount` is positive only when the order has at least 2 settled payment rows and `settled_payment_total > expected_net_amount`; otherwise it is `0.00`
- `over_refund_amount` is positive only when `completed_refund_total > settled_payment_total`; otherwise it is `0.00`
- `net_gap_amount = abs(actual_net_amount - expected_net_amount)`
- An order is an exception when at least one of these is true:
  - `duplicate_charge_amount > 0`
  - `over_refund_amount > 0`
  - `open_refund_total > 0`
- `exception_types` must be a pipe-delimited string using this fixed type order: `duplicate_charge`, `over_refund`, `open_refund`
- `review_priority = critical` when `over_refund_amount > 0`
- `review_priority = high` when `duplicate_charge_amount > 0` and `open_refund_total > 0` but there is no over-refund
- Otherwise `review_priority = medium`
- `latest_payment_at` is the latest `posted_at` among settled payment rows for the order; leave blank if there are no settled payments
- `latest_refund_at` is the latest `requested_at` among refund rows whose status is either `completed` or `pending`; leave blank if there are none
- `settled_payment_ids` is the semicolon-delimited list of settled `payment_id` values in the required sorted order
- `open_refund_ids` is the semicolon-delimited list of pending `refund_id` values in the required sorted order; leave blank when there are none

Write `reconciliation_exceptions.csv` with exactly these columns in this exact order:
1. `order_id`
2. `customer_region`
3. `expected_net_amount`
4. `settled_payment_total`
5. `completed_refund_total`
6. `open_refund_total`
7. `actual_net_amount`
8. `duplicate_charge_amount`
9. `over_refund_amount`
10. `net_gap_amount`
11. `exception_types`
12. `review_priority`
13. `latest_payment_at`
14. `latest_refund_at`
15. `settled_payment_ids`
16. `open_refund_ids`

Output requirements:
- Export only exception orders
- Sort rows by review priority severity in this order: `critical`, `high`, `medium`, then by `order_id` ascending
- Round all numeric amount columns in the CSV to 2 decimals
- Keep blank timestamp or ID-list fields empty rather than writing placeholder text

Write `reconciliation_summary.json` with exactly these top-level keys:
- `orders_processed`
- `exception_order_count`
- `priority_counts`
- `duplicate_charge_orders`
- `over_refund_orders`
- `open_refund_orders`
- `total_duplicate_charge_amount`
- `total_over_refund_amount`
- `total_open_refund_amount`
- `highest_net_gap_amount`
- `orders_with_negative_actual_net`

Summary requirements:
- `priority_counts` must contain `critical`, `high`, and `medium`
- `orders_with_negative_actual_net` must be sorted ascending
- Round all summary amount values to 2 decimals
