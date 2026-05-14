from __future__ import annotations

from datetime import date
from decimal import Decimal


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def days_past_due(invoice: dict, run_date: date) -> int:
    due_date = parse_date(invoice["due_date"])
    return max((run_date - due_date).days, 0)


def determine_action(subscription: dict, invoice: dict, amounts: dict, policy: dict, run_date: date) -> tuple[str, str]:
    renewal_due = parse_date(subscription["renewal_date"]) <= run_date
    outstanding_amount = Decimal(amounts["outstanding_amount"])

    if not renewal_due and outstanding_amount == Decimal("0.00"):
        return "monitor", "upcoming_only"

    if subscription["collection_method"] == "send_invoice" and renewal_due:
        return "send_manual_invoice", "manual_collection_required"

    if outstanding_amount > Decimal("0.00"):
        if subscription["default_payment_method_status"] != "usable":
            return "collect_payment_method", "payment_method_missing"
        if invoice["next_payment_attempt"]:
            return "retry_payment", "retry_window_open"
        return "pause_entitlement", "collection_exhausted"

    return "charge_renewal", "renewal_ready"
