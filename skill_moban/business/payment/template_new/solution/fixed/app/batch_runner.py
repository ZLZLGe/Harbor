from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from calculators import compute_amounts, parse_date
from loaders import load_all
from policy import determine_action


ROW_FIELDS = [
    "subscription_id",
    "customer_id",
    "currency",
    "current_status",
    "collection_method",
    "latest_invoice_id",
    "renewal_amount_due",
    "adjustment_amount",
    "tax_amount",
    "outstanding_amount",
    "action_bucket",
    "action_reason",
    "next_step",
    "evidence",
]


def _money_text(value) -> str:
    return f"{value:.2f}"


def build_row(
    subscription: dict,
    invoice: dict,
    change_requests: list[dict],
    usage_rows: list[dict],
    prices_by_id: dict[str, dict],
    policy: dict,
    run_date: date,
) -> dict:
    amounts = compute_amounts(
        subscription=subscription,
        invoice=invoice,
        change_requests=change_requests,
        usage_rows=usage_rows,
        prices_by_id=prices_by_id,
        tax_rates=policy["tax_rates"],
    )
    action_bucket, action_reason = determine_action(subscription, invoice, amounts, policy, run_date)
    evidence = {
        "subscription_id": subscription["subscription_id"],
        "invoice_id": invoice["invoice_id"],
        "plan_price_id": amounts["target_price_id"],
        "metered_price_ids": subscription["metered_price_ids"],
        "applied_change_request_id": amounts["applied_change_request_id"],
        "customer_tax_country": subscription["customer_tax_country"],
    }
    return {
        "subscription_id": subscription["subscription_id"],
        "customer_id": subscription["customer_id"],
        "currency": subscription["currency"],
        "current_status": subscription["current_status"],
        "collection_method": subscription["collection_method"],
        "latest_invoice_id": invoice["invoice_id"],
        "renewal_amount_due": _money_text(amounts["renewal_amount_due"]),
        "adjustment_amount": _money_text(amounts["adjustment_amount"]),
        "tax_amount": _money_text(amounts["tax_amount"]),
        "outstanding_amount": _money_text(amounts["outstanding_amount"]),
        "action_bucket": action_bucket,
        "action_reason": action_reason,
        "next_step": policy["next_steps"][action_bucket],
        "evidence": json.dumps(evidence, sort_keys=True),
    }


def build_outputs(data_root: Path) -> tuple[list[dict], dict]:
    loaded = load_all(data_root)
    manifest = loaded["manifest"]
    policy = loaded["policy"]
    prices_by_id = loaded["prices_by_id"]
    subscriptions_by_id = loaded["subscriptions_by_id"]
    invoices_by_subscription = loaded["invoices_by_subscription"]
    changes_by_subscription = loaded["changes_by_subscription"]
    usage_by_subscription = loaded["usage_by_subscription"]

    run_date = parse_date(manifest["run_date"])
    rows: list[dict] = []
    action_counts = {
        "charge_renewal": 0,
        "send_manual_invoice": 0,
        "retry_payment": 0,
        "collect_payment_method": 0,
        "pause_entitlement": 0,
        "monitor": 0,
    }

    for subscription_id in manifest["batch_scope"]["subscription_ids"]:
        subscription = subscriptions_by_id[subscription_id]
        invoice = invoices_by_subscription[subscription_id]
        row = build_row(
            subscription=subscription,
            invoice=invoice,
            change_requests=changes_by_subscription.get(subscription_id, []),
            usage_rows=usage_by_subscription.get(subscription_id, []),
            prices_by_id=prices_by_id,
            policy=policy,
            run_date=run_date,
        )
        rows.append(row)
        action_counts[row["action_bucket"]] += 1

    blocked_set = set(policy["blocked_action_buckets"])
    blocked_ids = sorted(row["subscription_id"] for row in rows if row["action_bucket"] in blocked_set)
    needing_action = [row for row in rows if row["action_bucket"] != "monitor"]
    total_renewal = sum(float(row["renewal_amount_due"]) for row in rows)
    total_outstanding = sum(float(row["outstanding_amount"]) for row in rows)

    largest_adjustment = max(rows, key=lambda row: abs(float(row["adjustment_amount"])))
    highest_outstanding = max(rows, key=lambda row: float(row["outstanding_amount"]))

    summary = {
        "workspace_id": manifest["workspace_id"],
        "run_date": manifest["run_date"],
        "totals": {
            "subscriptions_reviewed": len(rows),
            "subscriptions_needing_action": len(needing_action),
            "total_renewal_amount_due": round(total_renewal, 2),
            "total_outstanding_amount": round(total_outstanding, 2),
        },
        "action_counts": action_counts,
        "blocked_subscription_ids": blocked_ids,
        "notes": [
            f"Largest absolute adjustment: {largest_adjustment['subscription_id']}.",
            f"Highest outstanding amount: {highest_outstanding['subscription_id']}.",
        ],
    }
    return rows, summary


def write_outputs(rows: list[dict], summary: dict, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "billing_actions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    (output_root / "billing_run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
