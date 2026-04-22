from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


DATA_ROOT = Path(os.environ.get("BOARD_DATA_ROOT", "/app/data"))
MONTHS = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
Q1_MONTHS = set(MONTHS[:3])
Q2_MONTHS = set(MONTHS[3:])
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
CHANNELS = ["Organic", "Paid Search", "Paid Social", "Partner"]
KEY_FIELDS = ["month", "segment", "channel"]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_float(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def _round_rate(value: float) -> float:
    return round(value, 4)


def _round_value(value: float) -> float:
    return round(value, 2)


def _average_metric(rows: list[dict[str, Any]], field: str, *, digits: int) -> float:
    values = [_to_float(row[field]) for row in rows if row.get(field, "") not in ("", None)]
    if not values:
        return 0.0
    return round(sum(values) / len(values), digits)


def compute_reference_metrics() -> list[dict[str, Any]]:
    subscriptions = read_csv_rows(DATA_ROOT / "subscriptions" / "account_month_status.csv")
    usage = read_csv_rows(DATA_ROOT / "product" / "usage_monthly.csv")
    tickets = read_csv_rows(DATA_ROOT / "support" / "tickets.csv")
    spend = read_csv_rows(DATA_ROOT / "marketing" / "channel_spend.csv")
    spend_map = {(row["month"], row["channel"]): float(row["spend_usd"]) for row in spend}

    rows: list[dict[str, Any]] = []
    for month in MONTHS:
        for segment in SEGMENTS:
            for channel in CHANNELS:
                sub_rows = [
                    row
                    for row in subscriptions
                    if row["month"] == month and row["segment"] == segment and row["channel"] == channel
                ]
                usage_rows = [
                    row
                    for row in usage
                    if row["month"] == month and row["segment"] == segment and row["channel"] == channel
                ]
                ticket_rows = [
                    row
                    for row in tickets
                    if row["month"] == month and row["segment"] == segment and row["channel"] == channel
                ]

                start_active = [row for row in sub_rows if float(row["start_arr_usd"]) > 0]
                retained = [
                    row for row in sub_rows if float(row["start_arr_usd"]) > 0 and float(row["end_arr_usd"]) > 0
                ]
                new_paid = [
                    row for row in sub_rows if float(row["start_arr_usd"]) == 0 and float(row["end_arr_usd"]) > 0
                ]

                new_arr = sum(float(row["end_arr_usd"]) for row in new_paid)
                expansion_arr = sum(
                    max(float(row["end_arr_usd"]) - float(row["start_arr_usd"]), 0.0)
                    for row in sub_rows
                    if float(row["start_arr_usd"]) > 0 and float(row["end_arr_usd"]) > 0
                )
                contraction_arr = sum(
                    max(float(row["start_arr_usd"]) - float(row["end_arr_usd"]), 0.0)
                    for row in sub_rows
                    if float(row["start_arr_usd"]) > 0 and float(row["end_arr_usd"]) > 0
                )
                churned_arr = sum(
                    float(row["start_arr_usd"])
                    for row in sub_rows
                    if float(row["start_arr_usd"]) > 0 and float(row["end_arr_usd"]) == 0
                )
                start_arr = sum(float(row["start_arr_usd"]) for row in start_active)
                retained_end_arr = sum(float(row["end_arr_usd"]) for row in retained)
                end_arr_total = sum(float(row["end_arr_usd"]) for row in sub_rows)
                active_accounts = sum(1 for row in sub_rows if float(row["end_arr_usd"]) > 0)

                new_paid_count = len(new_paid)
                activated_count = sum(
                    int(row["activated_within_14d"]) for row in usage_rows if row["new_paid_account"] == "1"
                )
                pql_total = sum(int(row["pql_flag"]) for row in usage_rows)
                pql_paid = sum(int(row["paid_conversion_within_30d"]) for row in usage_rows)
                ticket_count = sum(int(row["tickets_opened"]) for row in ticket_rows)
                p1_total = sum(int(row["p1_tickets"]) for row in ticket_rows)
                p1_met = sum(int(row["p1_sla_met"]) for row in ticket_rows)

                cac_value: float | str = ""
                payback_value: float | str = ""
                if new_paid_count:
                    cac = spend_map[(month, channel)] / new_paid_count
                    avg_new_arr = new_arr / new_paid_count
                    payback = cac / ((avg_new_arr / 12.0) * 0.82)
                    cac_value = _round_value(cac)
                    payback_value = _round_value(payback)

                rows.append(
                    {
                        "month": month,
                        "segment": segment,
                        "channel": channel,
                        "new_arr": _round_value(new_arr),
                        "expansion_arr": _round_value(expansion_arr),
                        "contraction_arr": _round_value(contraction_arr),
                        "churned_arr": _round_value(churned_arr),
                        "net_arr_delta": _round_value(new_arr + expansion_arr - contraction_arr - churned_arr),
                        "mrr": _round_value(end_arr_total / 12.0),
                        "logo_retention_rate": _round_rate((len(retained) / len(start_active)) if start_active else 1.0),
                        "revenue_retention_rate": _round_rate((retained_end_arr / start_arr) if start_arr else 1.0),
                        "cac": cac_value,
                        "payback_months": payback_value,
                        "activation_rate": _round_rate((activated_count / new_paid_count) if new_paid_count else 1.0),
                        "pql_to_paid_rate": _round_rate((pql_paid / pql_total) if pql_total else 0.0),
                        "ticket_rate_per_100_accounts": _round_value((ticket_count / active_accounts * 100.0) if active_accounts else 0.0),
                        "p1_response_sla_rate": _round_rate((p1_met / p1_total) if p1_total else 1.0),
                    }
                )
    return rows


def build_metric_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(row["month"], row["segment"], row["channel"]): row for row in rows}


def summarize_slice(rows: list[dict[str, Any]], segment: str, channel: str) -> dict[str, Any]:
    slice_rows = [row for row in rows if row["segment"] == segment and row["channel"] == channel]
    q1_rows = [row for row in slice_rows if row["month"] in Q1_MONTHS]
    q2_rows = [row for row in slice_rows if row["month"] in Q2_MONTHS]
    return {
        "segment": segment,
        "channel": channel,
        "q1_net_arr_delta": _round_value(sum(_to_float(row["net_arr_delta"]) for row in q1_rows)),
        "q2_net_arr_delta": _round_value(sum(_to_float(row["net_arr_delta"]) for row in q2_rows)),
        "q1_logo_retention_rate": _average_metric(q1_rows, "logo_retention_rate", digits=4),
        "q2_logo_retention_rate": _average_metric(q2_rows, "logo_retention_rate", digits=4),
        "q1_revenue_retention_rate": _average_metric(q1_rows, "revenue_retention_rate", digits=4),
        "q2_revenue_retention_rate": _average_metric(q2_rows, "revenue_retention_rate", digits=4),
        "q1_cac": _average_metric(q1_rows, "cac", digits=2),
        "q2_cac": _average_metric(q2_rows, "cac", digits=2),
        "q1_payback_months": _average_metric(q1_rows, "payback_months", digits=2),
        "q2_payback_months": _average_metric(q2_rows, "payback_months", digits=2),
        "q2_activation_rate": _average_metric(q2_rows, "activation_rate", digits=4),
        "q2_ticket_rate_per_100_accounts": _average_metric(q2_rows, "ticket_rate_per_100_accounts", digits=2),
    }


def compute_q2_region_rollup(segment: str, channel: str) -> dict[str, dict[str, Any]]:
    invoices = read_csv_rows(DATA_ROOT / "orders" / "invoices.csv")
    subscriptions = read_csv_rows(DATA_ROOT / "subscriptions" / "account_month_status.csv")
    tickets = read_csv_rows(DATA_ROOT / "support" / "tickets.csv")
    usage = read_csv_rows(DATA_ROOT / "product" / "usage_monthly.csv")

    rollup: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "gross_usd": 0.0,
            "refund_usd": 0.0,
            "active_accounts": 0.0,
            "tickets_opened": 0.0,
            "p1_tickets": 0.0,
            "p1_sla_met": 0.0,
            "new_paid_accounts": 0.0,
            "activated_within_14d": 0.0,
            "pql_flag": 0.0,
            "paid_conversion_within_30d": 0.0,
        }
    )

    for row in invoices:
        if row["month"] in Q2_MONTHS and row["segment"] == segment and row["channel"] == channel:
            rollup[row["region"]]["gross_usd"] += float(row["gross_amount_usd"])
            rollup[row["region"]]["refund_usd"] += float(row["refund_amount_usd"])
    for row in subscriptions:
        if row["month"] in Q2_MONTHS and row["segment"] == segment and row["channel"] == channel:
            if float(row["end_arr_usd"]) > 0:
                rollup[row["region"]]["active_accounts"] += 1
    for row in tickets:
        if row["month"] in Q2_MONTHS and row["segment"] == segment and row["channel"] == channel:
            rollup[row["region"]]["tickets_opened"] += int(row["tickets_opened"])
            rollup[row["region"]]["p1_tickets"] += int(row["p1_tickets"])
            rollup[row["region"]]["p1_sla_met"] += int(row["p1_sla_met"])
    for row in usage:
        if row["month"] in Q2_MONTHS and row["segment"] == segment and row["channel"] == channel:
            rollup[row["region"]]["pql_flag"] += int(row["pql_flag"])
            rollup[row["region"]]["paid_conversion_within_30d"] += int(row["paid_conversion_within_30d"])
            if row["new_paid_account"] == "1":
                rollup[row["region"]]["new_paid_accounts"] += 1
                rollup[row["region"]]["activated_within_14d"] += int(row["activated_within_14d"])

    result: dict[str, dict[str, Any]] = {}
    for region, raw in rollup.items():
        gross = raw["gross_usd"]
        active = raw["active_accounts"]
        p1_total = raw["p1_tickets"]
        new_paid = raw["new_paid_accounts"]
        pql_total = raw["pql_flag"]
        result[region] = {
            "q2_refund_rate": _round_rate(raw["refund_usd"] / gross if gross else 0.0),
            "q2_ticket_rate_per_100_accounts": _round_value(raw["tickets_opened"] / active * 100.0 if active else 0.0),
            "q2_p1_response_sla_rate": _round_rate(raw["p1_sla_met"] / p1_total if p1_total else 1.0),
            "q2_activation_rate": _round_rate(raw["activated_within_14d"] / new_paid if new_paid else 1.0),
            "q2_pql_to_paid_rate": _round_rate(raw["paid_conversion_within_30d"] / pql_total if pql_total else 0.0),
            "refund_usd": raw["refund_usd"],
        }
    return result


def stringify_payload(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
