from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import yaml


TWOPLACES = Decimal("0.01")
DATA_ROOT = Path("/root/data")


def money(value) -> Decimal:
    return Decimal(str(value))


def q(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path):
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def recurring_amount(price: dict, quantity: int) -> Decimal:
    return money(price["unit_amount_decimal"]) * Decimal(quantity)


def main() -> None:
    manifest = load_json(DATA_ROOT / "billing_manifest.json")
    catalog = load_json(DATA_ROOT / "plan_catalog_seed.json")
    subs = {row["subscription_id"]: row for row in load_ndjson(DATA_ROOT / "subscription_snapshot.ndjson")}
    invoices = {row["subscription_id"]: row for row in load_ndjson(DATA_ROOT / "invoice_snapshot.ndjson")}
    changes = load_csv(DATA_ROOT / "change_requests.csv")
    usage = load_csv(DATA_ROOT / "usage_rollups.csv")
    policy = yaml.safe_load((DATA_ROOT / "billing_policy.yaml").read_text(encoding="utf-8"))

    prices_by_id = {row["id"]: row for row in catalog["prices"]}
    changes_by_sub: dict[str, list[dict]] = {}
    for row in changes:
        changes_by_sub.setdefault(row["subscription_id"], []).append(row)
    usage_by_sub: dict[str, list[dict]] = {}
    for row in usage:
        usage_by_sub.setdefault(row["subscription_id"], []).append(row)

    run_date = parse_date(manifest["run_date"])

    for subscription_id in manifest["batch_scope"]["subscription_ids"]:
        subscription = subs[subscription_id]
        invoice = invoices[subscription_id]
        applicable_change = None
        for row in changes_by_sub.get(subscription_id, []):
            if row["status"] != "approved":
                continue
            if parse_date(row["effective_date"]) <= parse_date(subscription["renewal_date"]):
                applicable_change = row

        target_price_id = subscription["plan_price_id"]
        target_quantity = int(subscription["quantity"])
        if applicable_change:
            target_price_id = applicable_change["target_price_id"]
            target_quantity = int(applicable_change["target_quantity"])

        licensed_total = recurring_amount(prices_by_id[target_price_id], target_quantity)
        usage_total = Decimal("0")
        for row in usage_by_sub.get(subscription_id, []):
            usage_total += money(prices_by_id[row["price_id"]]["unit_amount_decimal"]) * money(row["usage_quantity"])

        adjustment = Decimal("0")
        if applicable_change and applicable_change["apply_timing"] == "current_cycle":
            start = parse_date(subscription["current_period_start"])
            end = parse_date(subscription["current_period_end"])
            effective = parse_date(applicable_change["effective_date"])
            old_amount = recurring_amount(prices_by_id[subscription["plan_price_id"]], int(subscription["quantity"]))
            new_amount = recurring_amount(prices_by_id[applicable_change["target_price_id"]], int(applicable_change["target_quantity"]))
            total_days = max((end - start).days, 1)
            remaining_days = max((end - effective).days, 0)
            adjustment = (new_amount - old_amount) * Decimal(remaining_days) / Decimal(total_days)

        renewal_total = q(licensed_total + usage_total)
        adjustment = q(adjustment)
        subtotal = renewal_total + adjustment
        if subtotal < 0:
            subtotal = Decimal("0")
        tax = q(subtotal * money(policy["tax_rates"][subscription["customer_tax_country"]]))
        outstanding = q(money(invoice["amount_remaining"]))

        if subscription["collection_method"] == "send_invoice" and (
            parse_date(subscription["renewal_date"]) <= run_date or outstanding > 0
        ):
            action = "send_manual_invoice"
        elif outstanding > 0 and subscription["collection_method"] == "charge_automatically":
            due_days = max((run_date - parse_date(invoice["due_date"])).days, 0)
            if (
                int(invoice["attempt_count"]) >= int(policy["collection_exhausted"]["pause_after_attempt_count"])
                or due_days >= int(policy["collection_exhausted"]["pause_after_days_past_due"])
            ):
                action = "pause_entitlement"
            elif subscription["default_payment_method_status"] != "usable":
                action = "collect_payment_method"
            elif invoice["next_payment_attempt"] and parse_date(invoice["next_payment_attempt"]) >= run_date:
                action = "retry_payment"
            else:
                action = "pause_entitlement"
        elif parse_date(subscription["renewal_date"]) > run_date:
            action = "monitor"
        else:
            action = "charge_renewal"

        print(
            json.dumps(
                {
                    "subscription_id": subscription_id,
                    "renewal_amount_due": f"{renewal_total:.2f}",
                    "adjustment_amount": f"{adjustment:.2f}",
                    "tax_amount": f"{tax:.2f}",
                    "outstanding_amount": f"{outstanding:.2f}",
                    "applied_change_request_id": applicable_change["change_request_id"] if applicable_change else None,
                    "suggested_action": action,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
