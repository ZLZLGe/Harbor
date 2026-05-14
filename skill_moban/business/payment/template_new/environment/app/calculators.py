from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal("0.01")


def money(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def recurring_amount(price: dict, quantity: int) -> Decimal:
    return money(price["unit_amount_decimal"]) * Decimal(quantity)


def metered_amount(usage_rows: list[dict], prices_by_id: dict[str, dict]) -> Decimal:
    total = Decimal("0")
    for row in usage_rows:
        price = prices_by_id[row["price_id"]]
        total += money(price["unit_amount_decimal"]) * money(row["usage_quantity"])
    return quantize_money(total)


def select_effective_change(subscription: dict, change_requests: list[dict]) -> dict | None:
    renewal_date = parse_date(subscription["renewal_date"])
    selected = None
    for row in change_requests:
        if row["status"] != "approved":
            continue
        if parse_date(row["effective_date"]) <= renewal_date:
            selected = row
    return selected


def compute_adjustment_amount(subscription: dict, change_request: dict | None, prices_by_id: dict[str, dict]) -> Decimal:
    if change_request is None:
        return Decimal("0.00")
    if change_request["apply_timing"] != "current_cycle":
        return Decimal("0.00")

    current_period_start = parse_date(subscription["current_period_start"])
    current_period_end = parse_date(subscription["current_period_end"])
    effective_date = parse_date(change_request["effective_date"])
    if effective_date >= current_period_end:
        return Decimal("0.00")

    old_price = prices_by_id[subscription["plan_price_id"]]
    new_price = prices_by_id[change_request["target_price_id"]]
    old_amount = recurring_amount(old_price, int(subscription["quantity"]))
    new_amount = recurring_amount(new_price, int(change_request["target_quantity"]))
    delta = new_amount - old_amount

    total_days = max((current_period_end - current_period_start).days, 1)
    remaining_days = max((current_period_end - effective_date).days, 0)
    prorated = delta * Decimal(remaining_days) / Decimal(total_days)
    return quantize_money(prorated)


def compute_amounts(
    subscription: dict,
    invoice: dict,
    change_requests: list[dict],
    usage_rows: list[dict],
    prices_by_id: dict[str, dict],
    tax_rates: dict[str, float],
) -> dict:
    change_request = select_effective_change(subscription, change_requests)
    target_price_id = subscription["plan_price_id"]
    target_plan_id = subscription["plan_id"]
    target_quantity = int(subscription["quantity"])
    if change_request is not None:
        target_price_id = change_request["target_price_id"]
        target_plan_id = change_request["target_plan_id"]
        target_quantity = int(change_request["target_quantity"])

    licensed_price = prices_by_id[target_price_id]
    licensed_total = recurring_amount(licensed_price, target_quantity)
    usage_total = metered_amount(usage_rows, prices_by_id)
    renewal_amount_due = quantize_money(licensed_total + usage_total)

    # TODO: current-cycle changes must flow into an auditable adjustment amount.
    adjustment_amount = Decimal("0.00")

    tax_rate = money(tax_rates[subscription["customer_tax_country"]])
    taxable_subtotal = renewal_amount_due + adjustment_amount
    if taxable_subtotal < Decimal("0.00"):
        taxable_subtotal = Decimal("0.00")
    tax_amount = quantize_money(taxable_subtotal * tax_rate)

    outstanding_amount = quantize_money(money(invoice["amount_remaining"]))

    return {
        "renewal_amount_due": renewal_amount_due,
        "adjustment_amount": adjustment_amount,
        "tax_amount": tax_amount,
        "outstanding_amount": outstanding_amount,
        "target_plan_id": target_plan_id,
        "target_price_id": target_price_id,
        "target_quantity": target_quantity,
        "applied_change_request_id": change_request["change_request_id"] if change_request else None,
    }
