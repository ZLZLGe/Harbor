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

    if subscription["collection_method"] == "send_invoice" and (renewal_due or outstanding_amount > Decimal("0.00")):
        return "send_manual_invoice", "manual_collection_required"

    if outstanding_amount > Decimal("0.00") and subscription["collection_method"] == "charge_automatically":
        past_due_days = days_past_due(invoice, run_date)
        if (
            int(invoice["attempt_count"]) >= int(policy["collection_exhausted"]["pause_after_attempt_count"])
            or past_due_days >= int(policy["collection_exhausted"]["pause_after_days_past_due"])
        ):
            return "pause_entitlement", "collection_exhausted"
        if subscription["default_payment_method_status"] != "usable":
            return "collect_payment_method", "payment_method_missing"
        if (
            invoice["next_payment_attempt"]
            and int(invoice["attempt_count"]) > 0
            and int(invoice["attempt_count"]) <= int(policy["retry_rules"]["max_attempts"])
            and parse_date(invoice["next_payment_attempt"]) >= run_date
        ):
            return "retry_payment", "retry_window_open"
        return "pause_entitlement", "collection_exhausted"

    if not renewal_due:
        return "monitor", "upcoming_only"

    return "charge_renewal", "renewal_ready"
