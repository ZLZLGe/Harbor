#!/bin/bash
set -euo pipefail

cat > /root/reconcile_ledgers.py <<'PY'
import json

import pandas as pd


PAYMENTS_PATH = "/root/payments_ledger.csv"
REFUNDS_PATH = "/root/refund_ledger.csv"
OUTPUT_PATH = "/root/reconciliation_exceptions.csv"
SUMMARY_PATH = "/root/reconciliation_summary.json"

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2}
EXCEPTION_ORDER = [
    ("duplicate_charge", "duplicate_charge_amount"),
    ("over_refund", "over_refund_amount"),
    ("open_refund", "open_refund_total"),
]


def rounded(value: float) -> float:
    return round(float(value), 2)


payments = pd.read_csv(PAYMENTS_PATH)
refunds = pd.read_csv(REFUNDS_PATH)

payments = payments.sort_values(["order_id", "posted_at", "payment_id"]).reset_index(drop=True)
refunds = refunds.sort_values(["order_id", "requested_at", "refund_id"]).reset_index(drop=True)

all_orders = sorted(set(payments["order_id"]) | set(refunds["order_id"]))
records = []

for order_id in all_orders:
    payment_rows = payments[payments["order_id"] == order_id]
    refund_rows = refunds[refunds["order_id"] == order_id]

    settled_rows = payment_rows[payment_rows["payment_status"] == "settled"]
    completed_refunds = refund_rows[refund_rows["refund_status"] == "completed"]
    pending_refunds = refund_rows[refund_rows["refund_status"] == "pending"]
    review_refunds = refund_rows[refund_rows["refund_status"].isin(["completed", "pending"])]

    expected_net_amount = rounded(payment_rows["intended_order_amount"].iloc[0]) if not payment_rows.empty else 0.0
    settled_payment_total = rounded(settled_rows["charged_amount"].sum())
    completed_refund_total = rounded(completed_refunds["refund_amount"].sum())
    open_refund_total = rounded(pending_refunds["refund_amount"].sum())
    actual_net_amount = rounded(settled_payment_total - completed_refund_total)

    duplicate_charge_amount = 0.0
    if len(settled_rows) >= 2 and settled_payment_total > expected_net_amount:
        duplicate_charge_amount = rounded(settled_payment_total - expected_net_amount)

    over_refund_amount = 0.0
    if completed_refund_total > settled_payment_total:
        over_refund_amount = rounded(completed_refund_total - settled_payment_total)

    net_gap_amount = rounded(abs(actual_net_amount - expected_net_amount))

    exception_types = [
        name
        for name, field in EXCEPTION_ORDER
        if (duplicate_charge_amount if field == "duplicate_charge_amount" else over_refund_amount if field == "over_refund_amount" else open_refund_total) > 0
    ]

    if not exception_types:
        continue

    if over_refund_amount > 0:
        review_priority = "critical"
    elif duplicate_charge_amount > 0 and open_refund_total > 0:
        review_priority = "high"
    else:
        review_priority = "medium"

    records.append(
        {
            "order_id": order_id,
            "customer_region": payment_rows["customer_region"].iloc[0] if not payment_rows.empty else "",
            "expected_net_amount": expected_net_amount,
            "settled_payment_total": settled_payment_total,
            "completed_refund_total": completed_refund_total,
            "open_refund_total": open_refund_total,
            "actual_net_amount": actual_net_amount,
            "duplicate_charge_amount": duplicate_charge_amount,
            "over_refund_amount": over_refund_amount,
            "net_gap_amount": net_gap_amount,
            "exception_types": "|".join(exception_types),
            "review_priority": review_priority,
            "latest_payment_at": settled_rows["posted_at"].iloc[-1] if not settled_rows.empty else "",
            "latest_refund_at": review_refunds["requested_at"].iloc[-1] if not review_refunds.empty else "",
            "settled_payment_ids": ";".join(settled_rows["payment_id"].tolist()),
            "open_refund_ids": ";".join(pending_refunds["refund_id"].tolist()),
            "_priority_rank": PRIORITY_RANK[review_priority],
        }
    )

exceptions = pd.DataFrame(records)
exceptions = exceptions.sort_values(["_priority_rank", "order_id"]).drop(columns=["_priority_rank"]).reset_index(drop=True)
exceptions = exceptions[
    [
        "order_id",
        "customer_region",
        "expected_net_amount",
        "settled_payment_total",
        "completed_refund_total",
        "open_refund_total",
        "actual_net_amount",
        "duplicate_charge_amount",
        "over_refund_amount",
        "net_gap_amount",
        "exception_types",
        "review_priority",
        "latest_payment_at",
        "latest_refund_at",
        "settled_payment_ids",
        "open_refund_ids",
    ]
]
exceptions.to_csv(OUTPUT_PATH, index=False)

summary = {
    "orders_processed": len(all_orders),
    "exception_order_count": int(len(exceptions)),
    "priority_counts": {
        "critical": int((exceptions["review_priority"] == "critical").sum()),
        "high": int((exceptions["review_priority"] == "high").sum()),
        "medium": int((exceptions["review_priority"] == "medium").sum()),
    },
    "duplicate_charge_orders": int((exceptions["duplicate_charge_amount"] > 0).sum()),
    "over_refund_orders": int((exceptions["over_refund_amount"] > 0).sum()),
    "open_refund_orders": int((exceptions["open_refund_total"] > 0).sum()),
    "total_duplicate_charge_amount": rounded(exceptions["duplicate_charge_amount"].sum()),
    "total_over_refund_amount": rounded(exceptions["over_refund_amount"].sum()),
    "total_open_refund_amount": rounded(exceptions["open_refund_total"].sum()),
    "highest_net_gap_amount": rounded(exceptions["net_gap_amount"].max()),
    "orders_with_negative_actual_net": sorted(
        exceptions.loc[exceptions["actual_net_amount"] < 0, "order_id"].tolist()
    ),
}

with open(SUMMARY_PATH, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
PY

python3 /root/reconcile_ledgers.py
