from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from settlement_quality.common import fmt_money, load_jsonl, load_merchants, money


TRACKED_EVENT_TYPES = {
    "charge",
    "refund",
    "chargeback",
    "manual_adjustment",
    "reserve_release",
}


def _include_event(event: dict[str, Any]) -> bool:
    return event["status"] == "posted" and event["event_type"] in TRACKED_EVENT_TYPES


def _resolve_batch_id(event: dict[str, Any]) -> str:
    return (event.get("processor_batch_id") or event.get("fallback_batch_id") or "").strip()


def _merchant_name(merchants: dict[str, dict[str, Any]], merchant_id: str) -> str:
    return merchants[merchant_id]["merchant_name"]


def _sorted_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        events,
        key=lambda item: (
            item["settlement_date"],
            item["occurred_at"],
            item["event_id"],
        ),
    )


def build_daily_rows(ledger_path: Path, merchants_path: Path) -> list[dict[str, str]]:
    merchants = load_merchants(merchants_path)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in load_jsonl(ledger_path):
        if _include_event(event):
            key = (event["settlement_date"], event["merchant_id"], event["currency"])
            groups[key].append(event)

    rows: list[dict[str, str]] = []
    for (settlement_date, merchant_id, currency), events in sorted(groups.items()):
        gross_amount = money("0")
        fee_amount = money("0")
        adjustment_amount = money("0")
        charge_count = 0
        adjustment_count = 0
        batch_id = ""
        ordered_events = _sorted_events(events)

        for event in ordered_events:
            event_type = event["event_type"]
            fee_amount += money(event["fee_amount"])
            if not batch_id:
                batch_id = _resolve_batch_id(event)
            if event_type == "charge":
                gross_amount += money(event["gross_amount"])
                charge_count += 1
            else:
                adjustment_amount += money(event["adjustment_amount"])
                adjustment_count += 1

        net_amount = gross_amount - fee_amount + adjustment_amount
        rows.append(
            {
                "report_type": "daily",
                "report_date": settlement_date,
                "merchant_id": merchant_id,
                "merchant_name": _merchant_name(merchants, merchant_id),
                "currency": currency,
                "processor_batch_id": batch_id,
                "event_count": str(len(ordered_events)),
                "charge_count": str(charge_count),
                "adjustment_count": str(adjustment_count),
                "gross_amount": fmt_money(gross_amount),
                "fee_amount": fmt_money(fee_amount),
                "adjustment_amount": fmt_money(adjustment_amount),
                "net_settlement_amount": fmt_money(net_amount),
            }
        )
    return rows


def build_monthly_rows(ledger_path: Path, merchants_path: Path) -> list[dict[str, str]]:
    merchants = load_merchants(merchants_path)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in load_jsonl(ledger_path):
        if _include_event(event):
            report_month = event["settlement_date"][:7]
            key = (report_month, event["merchant_id"], event["currency"])
            groups[key].append(event)

    rows: list[dict[str, str]] = []
    for (report_month, merchant_id, currency), events in sorted(groups.items()):
        gross_amount = money("0")
        fee_amount = money("0")
        adjustment_amount = money("0")
        charge_count = 0
        refund_count = 0
        chargeback_count = 0
        adjustment_count = 0
        ordered_events = _sorted_events(events)
        settlement_dates = [item["settlement_date"] for item in ordered_events]
        batch_ids = [_resolve_batch_id(item) for item in ordered_events]

        for event in ordered_events:
            event_type = event["event_type"]
            fee_amount += money(event["fee_amount"])
            if event_type == "charge":
                gross_amount += money(event["gross_amount"])
                charge_count += 1
            else:
                adjustment_amount += money(event["adjustment_amount"])
                adjustment_count += 1
                if event_type == "refund":
                    refund_count += 1
                if event_type == "chargeback":
                    chargeback_count += 1

        net_amount = gross_amount - fee_amount + adjustment_amount
        rows.append(
            {
                "report_type": "monthly",
                "report_month": report_month,
                "merchant_id": merchant_id,
                "merchant_name": _merchant_name(merchants, merchant_id),
                "currency": currency,
                "charge_count": str(charge_count),
                "refund_count": str(refund_count),
                "chargeback_count": str(chargeback_count),
                "adjustment_count": str(adjustment_count),
                "gross_amount": fmt_money(gross_amount),
                "fee_amount": fmt_money(fee_amount),
                "adjustment_amount": fmt_money(adjustment_amount),
                "net_settlement_amount": fmt_money(net_amount),
                "first_settlement_date": settlement_dates[0],
                "last_settlement_date": settlement_dates[-1],
                "first_batch_id": batch_ids[0],
                "last_batch_id": batch_ids[-1],
            }
        )
    return rows
