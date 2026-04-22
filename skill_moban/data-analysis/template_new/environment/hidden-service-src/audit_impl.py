#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


PORT = int(os.environ.get("BOARD_AUDIT_INTERNAL_PORT", os.environ.get("BOARD_AUDIT_PORT", "8321")))
ROOT = Path(os.environ.get("BOARD_DATA_ROOT", "/app/data"))
TRACE_PATH = Path(os.environ.get("BOARD_AUDIT_TRACE_PATH", "/tmp/board_audit_trace.jsonl"))
MANIFEST_ID = "saas-growth-board-2025h1-v1"
REQUIRED_DIMENSIONS = {
    "months": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"],
    "segments": ["SMB", "Mid-Market", "Enterprise"],
    "channels": ["Organic", "Paid Search", "Paid Social", "Partner"],
}
RATE_FIELDS = {
    "logo_retention_rate",
    "revenue_retention_rate",
    "activation_rate",
    "pql_to_paid_rate",
    "p1_response_sla_rate",
}
VALUE_FIELDS = [
    "new_arr",
    "expansion_arr",
    "contraction_arr",
    "churned_arr",
    "net_arr_delta",
    "mrr",
    "logo_retention_rate",
    "revenue_retention_rate",
    "cac",
    "payback_months",
    "activation_rate",
    "pql_to_paid_rate",
    "ticket_rate_per_100_accounts",
    "p1_response_sla_rate",
]
KEY_FIELDS = ["month", "segment", "channel"]
HELPER_SKILL_ROOT = Path("/app/.codex/skills/saas-board-metrics-diagnostics")
HELPER_SCRIPT_PATHS = [
    HELPER_SKILL_ROOT / "scripts" / "probe_metric_contract.py",
    HELPER_SKILL_ROOT / "scripts" / "recompute_metrics_diff.py",
    HELPER_SKILL_ROOT / "scripts" / "scan_growth_signals.py",
    HELPER_SKILL_ROOT / "scripts" / "package_and_submit_bundle.py",
]
HELPER_METRIC_IMPLEMENTATION_NOTES = {
    "new_paid_logo_definition": "For CAC, payback, and activation denominators, treat a new paid logo as a subscription row where start_arr_usd == 0 and end_arr_usd > 0 within the month x segment x channel slice.",
    "activation_numerator_source": "Activation still comes from summing usage_monthly.activated_within_14d only on rows where usage_monthly.new_paid_account == 1 for the same slice.",
    "pql_conversion_scope": "pql_to_paid_rate uses all usage rows in the slice via sum(paid_conversion_within_30d) / sum(pql_flag); do not restrict it to new-logo rows.",
    "ticket_rate_denominator": "ticket_rate_per_100_accounts uses the count of subscription rows with end_arr_usd > 0 in the slice, not active_seats or product activity rows.",
}
LAST_VALIDATION_RECORD: dict[str, Any] | None = None
LAST_SUBMISSION_RECORD: dict[str, Any] | None = None

try:
    TRACE_PATH.unlink(missing_ok=True)
except OSError:
    pass


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_float(value: str) -> float:
    if value == "":
        return 0.0
    return float(value)


def compute_reference_metrics() -> list[dict[str, Any]]:
    subscriptions = _load_csv(ROOT / "subscriptions" / "account_month_status.csv")
    usage = _load_csv(ROOT / "product" / "usage_monthly.csv")
    tickets = _load_csv(ROOT / "support" / "tickets.csv")
    spend = _load_csv(ROOT / "marketing" / "channel_spend.csv")

    spend_map = {(row["month"], row["channel"]): float(row["spend_usd"]) for row in spend}

    metrics: list[dict[str, Any]] = []
    for month in REQUIRED_DIMENSIONS["months"]:
        for segment in REQUIRED_DIMENSIONS["segments"]:
            for channel in REQUIRED_DIMENSIONS["channels"]:
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
                    row
                    for row in sub_rows
                    if float(row["start_arr_usd"]) > 0 and float(row["end_arr_usd"]) > 0
                ]
                new_paid = [
                    row
                    for row in sub_rows
                    if float(row["start_arr_usd"]) == 0 and float(row["end_arr_usd"]) > 0
                ]
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
                new_arr = sum(float(row["end_arr_usd"]) for row in new_paid)
                start_arr = sum(float(row["start_arr_usd"]) for row in start_active)
                retained_end_arr = sum(float(row["end_arr_usd"]) for row in retained)
                end_arr_total = sum(float(row["end_arr_usd"]) for row in sub_rows)
                active_accounts = sum(1 for row in sub_rows if float(row["end_arr_usd"]) > 0)

                new_paid_count = len(new_paid)
                activated_count = sum(int(row["activated_within_14d"]) for row in usage_rows if row["new_paid_account"] == "1")
                pql_total = sum(int(row["pql_flag"]) for row in usage_rows)
                pql_paid = sum(int(row["paid_conversion_within_30d"]) for row in usage_rows)
                ticket_count = sum(int(row["tickets_opened"]) for row in ticket_rows)
                p1_total = sum(int(row["p1_tickets"]) for row in ticket_rows)
                p1_met = sum(int(row["p1_sla_met"]) for row in ticket_rows)

                cac_value = ""
                payback_value = ""
                if new_paid_count:
                    cac = spend_map[(month, channel)] / new_paid_count
                    cac_value = round(cac, 2)
                    avg_new_arr = new_arr / new_paid_count
                    payback = cac / ((avg_new_arr / 12.0) * 0.82)
                    payback_value = round(payback, 2)

                row = {
                    "month": month,
                    "segment": segment,
                    "channel": channel,
                    "new_arr": round(new_arr, 2),
                    "expansion_arr": round(expansion_arr, 2),
                    "contraction_arr": round(contraction_arr, 2),
                    "churned_arr": round(churned_arr, 2),
                    "net_arr_delta": round(new_arr + expansion_arr - contraction_arr - churned_arr, 2),
                    "mrr": round(end_arr_total / 12.0, 2),
                    "logo_retention_rate": round((len(retained) / len(start_active)) if start_active else 1.0, 4),
                    "revenue_retention_rate": round((retained_end_arr / start_arr) if start_arr else 1.0, 4),
                    "cac": cac_value,
                    "payback_months": payback_value,
                    "activation_rate": round((activated_count / new_paid_count) if new_paid_count else 1.0, 4),
                    "pql_to_paid_rate": round((pql_paid / pql_total) if pql_total else 0.0, 4),
                    "ticket_rate_per_100_accounts": round((ticket_count / active_accounts * 100.0) if active_accounts else 0.0, 2),
                    "p1_response_sla_rate": round((p1_met / p1_total) if p1_total else 1.0, 4),
                }
                metrics.append(row)
    return metrics


REFERENCE_METRICS = compute_reference_metrics()
REFERENCE_BY_KEY = {
    tuple(row[field] for field in KEY_FIELDS): row for row in REFERENCE_METRICS
}


def _average_metric(rows: list[dict[str, Any]], field: str, *, digits: int) -> float:
    values = [_to_float(row[field]) for row in rows if row.get(field, "") not in ("", None)]
    if not values:
        return 0.0
    return round(sum(values) / len(values), digits)


def _available_helper_scripts() -> list[str]:
    return [str(path) for path in HELPER_SCRIPT_PATHS if path.exists()]


def _helper_mode_enabled() -> bool:
    return bool(_available_helper_scripts())


def _build_monthly_slice_metrics(metrics: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        (row["segment"], row["channel"], row["month"]): {
            "month": row["month"],
            "segment": row["segment"],
            "channel": row["channel"],
            "net_arr_delta": round(_to_float(str(row["net_arr_delta"])), 2),
            "revenue_retention_rate": round(_to_float(str(row["revenue_retention_rate"])), 4),
            "ticket_rate_per_100_accounts": round(_to_float(str(row["ticket_rate_per_100_accounts"])), 2),
            "activation_rate": round(_to_float(str(row["activation_rate"])), 4),
        }
        for row in metrics
    }


def _validate_submission_metrics_snapshot(rows: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list) or not rows:
        return ["metrics_snapshot must be a non-empty list of CSV-style rows"]

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"metrics_snapshot[{index}] must be an object")
            continue
        for field in KEY_FIELDS + VALUE_FIELDS:
            if field not in row:
                issues.append(f"metrics_snapshot[{index}] is missing field {field}")
                continue
            if not isinstance(row[field], str):
                issues.append(
                    f"metrics_snapshot[{index}].{field} must be a string sourced from CSV re-read semantics"
                )
                break
    return issues


def compute_expected_insights(metrics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    metrics = metrics or REFERENCE_METRICS
    subscriptions = _load_csv(ROOT / "subscriptions" / "account_month_status.csv")
    usage = _load_csv(ROOT / "product" / "usage_monthly.csv")
    tickets = _load_csv(ROOT / "support" / "tickets.csv")
    invoices = _load_csv(ROOT / "orders" / "invoices.csv")
    monthly_slice_metrics = _build_monthly_slice_metrics(metrics)

    q1_months = set(REQUIRED_DIMENSIONS["months"][:3])
    q2_months = set(REQUIRED_DIMENSIONS["months"][3:])

    slice_metrics: dict[tuple[str, str], dict[str, Any]] = {}
    for segment in REQUIRED_DIMENSIONS["segments"]:
        for channel in REQUIRED_DIMENSIONS["channels"]:
            metric_rows = [row for row in metrics if row["segment"] == segment and row["channel"] == channel]
            q1_rows = [row for row in metric_rows if row["month"] in q1_months]
            q2_rows = [row for row in metric_rows if row["month"] in q2_months]

            q1_cac = _average_metric(q1_rows, "cac", digits=2)
            q2_cac = _average_metric(q2_rows, "cac", digits=2)
            q1_payback = _average_metric(q1_rows, "payback_months", digits=2)
            q2_payback = _average_metric(q2_rows, "payback_months", digits=2)
            q1_net_arr = round(sum(_to_float(row["net_arr_delta"]) for row in q1_rows), 2)
            q2_net_arr = round(sum(_to_float(row["net_arr_delta"]) for row in q2_rows), 2)
            q1_logo_retention = _average_metric(q1_rows, "logo_retention_rate", digits=4)
            q2_logo_retention = _average_metric(q2_rows, "logo_retention_rate", digits=4)
            q1_revenue_retention = _average_metric(q1_rows, "revenue_retention_rate", digits=4)
            q2_revenue_retention = _average_metric(q2_rows, "revenue_retention_rate", digits=4)
            q2_activation = _average_metric(q2_rows, "activation_rate", digits=4)
            q2_ticket_rate = _average_metric(q2_rows, "ticket_rate_per_100_accounts", digits=2)

            healthy_growth_score = round(
                q2_net_arr
                * max(q2_revenue_retention, 0.0)
                * max(q2_activation, 0.05)
                / max(q2_payback or 999.0, 1.0),
                2,
            )
            risk_score = round(
                max(0.0, -q2_net_arr) * 2.0
                + max(0.0, 1.0 - q2_revenue_retention) * 50000.0
                + max(0.0, 1.0 - q2_logo_retention) * 25000.0
                + q2_ticket_rate * 50.0
                + max(0.0, q2_payback - 12.0) * 1000.0,
                2,
            )
            retention_deterioration = round(
                max(0.0, q1_logo_retention - q2_logo_retention) * 100.0
                + max(0.0, q1_revenue_retention - q2_revenue_retention) * 100.0,
                2,
            )

            slice_metrics[(segment, channel)] = {
                "segment": segment,
                "channel": channel,
                "q1_net_arr_delta": q1_net_arr,
                "q2_net_arr_delta": q2_net_arr,
                "q1_logo_retention_rate": q1_logo_retention,
                "q2_logo_retention_rate": q2_logo_retention,
                "q1_revenue_retention_rate": q1_revenue_retention,
                "q2_revenue_retention_rate": q2_revenue_retention,
                "q2_activation_rate": q2_activation,
                "q2_ticket_rate_per_100_accounts": q2_ticket_rate,
                "q1_cac": q1_cac,
                "q2_cac": q2_cac,
                "q1_payback_months": q1_payback,
                "q2_payback_months": q2_payback,
                "healthy_growth_score": healthy_growth_score,
                "risk_score": risk_score,
                "retention_deterioration_score": retention_deterioration,
            }

    region_signals: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
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
        if row["month"] in q2_months:
            key = (row["segment"], row["channel"], row["region"])
            region_signals[key]["gross_usd"] += float(row["gross_amount_usd"])
            region_signals[key]["refund_usd"] += float(row["refund_amount_usd"])

    for row in subscriptions:
        if row["month"] in q2_months:
            key = (row["segment"], row["channel"], row["region"])
            if float(row["end_arr_usd"]) > 0:
                region_signals[key]["active_accounts"] += 1

    for row in tickets:
        if row["month"] in q2_months:
            key = (row["segment"], row["channel"], row["region"])
            region_signals[key]["tickets_opened"] += int(row["tickets_opened"])
            region_signals[key]["p1_tickets"] += int(row["p1_tickets"])
            region_signals[key]["p1_sla_met"] += int(row["p1_sla_met"])

    for row in usage:
        if row["month"] in q2_months:
            key = (row["segment"], row["channel"], row["region"])
            region_signals[key]["pql_flag"] += int(row["pql_flag"])
            region_signals[key]["paid_conversion_within_30d"] += int(row["paid_conversion_within_30d"])
            if row["new_paid_account"] == "1":
                region_signals[key]["new_paid_accounts"] += 1
                region_signals[key]["activated_within_14d"] += int(row["activated_within_14d"])

    region_summary: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, raw in region_signals.items():
        gross = raw["gross_usd"]
        active = raw["active_accounts"]
        p1_total = raw["p1_tickets"]
        new_paid = raw["new_paid_accounts"]
        pql_total = raw["pql_flag"]
        refund_rate = raw["refund_usd"] / gross if gross else 0.0
        ticket_rate = raw["tickets_opened"] / active * 100.0 if active else 0.0
        sla_rate = raw["p1_sla_met"] / p1_total if p1_total else 1.0
        activation_rate = raw["activated_within_14d"] / new_paid if new_paid else 1.0
        pql_to_paid_rate = raw["paid_conversion_within_30d"] / pql_total if pql_total else 0.0
        support_product_score = round(
            ticket_rate
            + refund_rate * 1000.0
            + max(0.0, 1.0 - activation_rate) * 100.0
            + max(0.0, 1.0 - sla_rate) * 100.0,
            2,
        )
        region_summary[key] = {
            "segment": key[0],
            "channel": key[1],
            "region": key[2],
            "q2_refund_rate": round(refund_rate, 4),
            "q2_ticket_rate_per_100_accounts": round(ticket_rate, 2),
            "q2_p1_response_sla_rate": round(sla_rate, 4),
            "q2_activation_rate": round(activation_rate, 4),
            "q2_pql_to_paid_rate": round(pql_to_paid_rate, 4),
            "support_product_score": support_product_score,
        }

    channel_summary: dict[str, dict[str, Any]] = {}
    for channel in REQUIRED_DIMENSIONS["channels"]:
        relevant = [value for value in slice_metrics.values() if value["channel"] == channel]
        q2_activation = round(sum(float(row["q2_activation_rate"]) for row in relevant) / len(relevant), 4)
        q1_cac = round(sum(float(row["q1_cac"]) for row in relevant) / len(relevant), 2)
        q2_cac = round(sum(float(row["q2_cac"]) for row in relevant) / len(relevant), 2)
        q1_payback = round(sum(float(row["q1_payback_months"]) for row in relevant) / len(relevant), 2)
        q2_payback = round(sum(float(row["q2_payback_months"]) for row in relevant) / len(relevant), 2)
        efficiency_score = round(q2_cac * max(q2_payback, 1.0) / max(q2_activation, 0.05), 2)
        channel_summary[channel] = {
            "channel": channel,
            "q1_cac": q1_cac,
            "q2_cac": q2_cac,
            "q1_payback_months": q1_payback,
            "q2_payback_months": q2_payback,
            "q2_activation_rate": q2_activation,
            "efficiency_score": efficiency_score,
        }

    growth = max(slice_metrics.values(), key=lambda row: (row["healthy_growth_score"], row["q2_net_arr_delta"]))
    risk = max(slice_metrics.values(), key=lambda row: (row["risk_score"], -row["q2_net_arr_delta"]))
    retention = max(
        slice_metrics.values(),
        key=lambda row: (row["retention_deterioration_score"], row["risk_score"]),
    )
    efficiency = max(channel_summary.values(), key=lambda row: (row["efficiency_score"], row["q2_cac"]))
    risk_region = max(
        [
            row
            for row in region_summary.values()
            if row["segment"] == risk["segment"] and row["channel"] == risk["channel"]
        ],
        key=lambda row: (
            row["q2_refund_rate"],
            row["q2_ticket_rate_per_100_accounts"],
            -row["q2_activation_rate"],
        ),
    )
    risk_region_key = (risk["segment"], risk["channel"], risk_region["region"])
    risk_slice_refunds = sum(
        raw["refund_usd"]
        for key, raw in region_signals.items()
        if key[0] == risk["segment"] and key[1] == risk["channel"]
    )
    focus_region_refund_share = round(
        (region_signals[risk_region_key]["refund_usd"] / risk_slice_refunds) if risk_slice_refunds else 0.0,
        4,
    )
    monthly_signal_chain = [
        {
            "month": month,
            "net_arr_delta": monthly_slice_metrics[(risk["segment"], risk["channel"], month)]["net_arr_delta"],
            "revenue_retention_rate": monthly_slice_metrics[(risk["segment"], risk["channel"], month)][
                "revenue_retention_rate"
            ],
            "ticket_rate_per_100_accounts": monthly_slice_metrics[(risk["segment"], risk["channel"], month)][
                "ticket_rate_per_100_accounts"
            ],
            "activation_rate": monthly_slice_metrics[(risk["segment"], risk["channel"], month)]["activation_rate"],
        }
        for month in REQUIRED_DIMENSIONS["months"][3:]
    ]
    break_month = next(
        (
            row["month"]
            for row in monthly_signal_chain
            if row["net_arr_delta"] < 0.0 or row["revenue_retention_rate"] < 0.9
        ),
        monthly_signal_chain[-1]["month"],
    )
    control_candidates = [
        row
        for row in slice_metrics.values()
        if row["segment"] == risk["segment"] and row["channel"] != risk["channel"] and row["q2_net_arr_delta"] > 0.0
    ]
    control_slice = max(
        control_candidates,
        key=lambda row: (
            row["q2_revenue_retention_rate"],
            row["q2_net_arr_delta"],
            -row["q2_ticket_rate_per_100_accounts"],
        ),
    )
    support_product = max(
        region_summary.values(),
        key=lambda row: (row["support_product_score"], row["q2_refund_rate"]),
    )

    return {
        "growth": {
            **growth,
            "delta_vs_baseline": round(growth["q2_net_arr_delta"] - growth["q1_net_arr_delta"], 2),
        },
        "risk": {
            **risk,
            "focus_region": risk_region["region"],
            "q2_refund_rate": risk_region["q2_refund_rate"],
            "q2_ticket_rate_per_100_accounts": risk_region["q2_ticket_rate_per_100_accounts"],
            "q2_p1_response_sla_rate": risk_region["q2_p1_response_sla_rate"],
            "q2_activation_rate": risk_region["q2_activation_rate"],
            "focus_region_refund_share": focus_region_refund_share,
            "break_month": break_month,
            "monthly_signal_chain": monthly_signal_chain,
            "control_slice": {
                "segment": control_slice["segment"],
                "channel": control_slice["channel"],
                "q2_net_arr_delta": control_slice["q2_net_arr_delta"],
                "q2_revenue_retention_rate": control_slice["q2_revenue_retention_rate"],
                "q2_ticket_rate_per_100_accounts": control_slice["q2_ticket_rate_per_100_accounts"],
            },
        },
        "efficiency": efficiency,
        "retention": retention,
        "support_product": support_product,
    }


EXPECTED_INSIGHTS = compute_expected_insights()


def _check_number(issues: list[str], section: str, field: str, actual: Any, expected: float, tolerance: float) -> None:
    try:
        value = float(actual)
    except (TypeError, ValueError):
        issues.append(f"{section}.{field} must be numeric")
        return
    if abs(value - expected) > tolerance:
        issues.append(f"{section}.{field} does not match the accepted audit result")


def _validate_ranked_finding(
    section: str,
    item: Any,
    expected: dict[str, Any],
    issues: list[str],
    *,
    string_fields: list[str],
    numeric_fields: dict[str, float],
) -> None:
    if not isinstance(item, dict):
        issues.append(f"{section} must contain objects")
        return
    for field in string_fields:
        if str(item.get(field, "")) != str(expected[field]):
            issues.append(f"{section}.{field} does not match the accepted audit result")
    for field, tolerance in numeric_fields.items():
        _check_number(issues, section, field, item.get(field), float(expected[field]), tolerance)
    evidence = str(item.get("evidence", "")).strip()
    if len(evidence) < 40:
        issues.append(f"{section}.evidence is too short")


def _validate_risk_chain(item: Any, expected: dict[str, Any], issues: list[str]) -> None:
    if not isinstance(item, dict):
        return

    _check_number(
        issues,
        "top_risk_drivers[0]",
        "focus_region_refund_share",
        item.get("focus_region_refund_share"),
        float(expected["focus_region_refund_share"]),
        1e-4,
    )
    if str(item.get("break_month", "")) != str(expected["break_month"]):
        issues.append("top_risk_drivers[0].break_month does not match the accepted audit result")

    monthly_chain = item.get("monthly_signal_chain")
    expected_chain = expected["monthly_signal_chain"]
    if not isinstance(monthly_chain, list) or len(monthly_chain) != len(expected_chain):
        issues.append("top_risk_drivers[0].monthly_signal_chain must contain the three Q2 monthly checkpoints")
    else:
        for index, (actual_row, expected_row) in enumerate(zip(monthly_chain, expected_chain)):
            if str(actual_row.get("month", "")) != str(expected_row["month"]):
                issues.append(
                    f"top_risk_drivers[0].monthly_signal_chain[{index}].month does not match the accepted audit result"
                )
                continue
            _check_number(
                issues,
                f"top_risk_drivers[0].monthly_signal_chain[{index}]",
                "net_arr_delta",
                actual_row.get("net_arr_delta"),
                float(expected_row["net_arr_delta"]),
                0.05,
            )
            _check_number(
                issues,
                f"top_risk_drivers[0].monthly_signal_chain[{index}]",
                "revenue_retention_rate",
                actual_row.get("revenue_retention_rate"),
                float(expected_row["revenue_retention_rate"]),
                1e-4,
            )
            _check_number(
                issues,
                f"top_risk_drivers[0].monthly_signal_chain[{index}]",
                "ticket_rate_per_100_accounts",
                actual_row.get("ticket_rate_per_100_accounts"),
                float(expected_row["ticket_rate_per_100_accounts"]),
                0.05,
            )
            _check_number(
                issues,
                f"top_risk_drivers[0].monthly_signal_chain[{index}]",
                "activation_rate",
                actual_row.get("activation_rate"),
                float(expected_row["activation_rate"]),
                1e-4,
            )

    control_slice = item.get("control_slice")
    expected_control = expected["control_slice"]
    if not isinstance(control_slice, dict):
        issues.append("top_risk_drivers[0].control_slice must be an object")
    else:
        for field in ["segment", "channel"]:
            if str(control_slice.get(field, "")) != str(expected_control[field]):
                issues.append(
                    f"top_risk_drivers[0].control_slice.{field} does not match the accepted audit result"
                )
        _check_number(
            issues,
            "top_risk_drivers[0].control_slice",
            "q2_net_arr_delta",
            control_slice.get("q2_net_arr_delta"),
            float(expected_control["q2_net_arr_delta"]),
            0.05,
        )
        _check_number(
            issues,
            "top_risk_drivers[0].control_slice",
            "q2_revenue_retention_rate",
            control_slice.get("q2_revenue_retention_rate"),
            float(expected_control["q2_revenue_retention_rate"]),
            1e-4,
        )
        _check_number(
            issues,
            "top_risk_drivers[0].control_slice",
            "q2_ticket_rate_per_100_accounts",
            control_slice.get("q2_ticket_rate_per_100_accounts"),
            float(expected_control["q2_ticket_rate_per_100_accounts"]),
            0.05,
        )


def _append_trace(event: str, payload: dict[str, Any]) -> None:
    # Keep audit-state diagnostics entirely in memory so the solver cannot
    # read server-side hints from the filesystem, even when running as root.
    _ = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "event": event,
        **payload,
    }


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_metric_rows(rows: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if len(rows) != len(REFERENCE_METRICS):
        issues.append(f"expected {len(REFERENCE_METRICS)} metric rows, got {len(rows)}")

    seen_keys: set[tuple[str, str, str]] = set()
    for row in rows:
        key = tuple(str(row.get(field, "")) for field in KEY_FIELDS)
        if key not in REFERENCE_BY_KEY:
            issues.append(f"unexpected metric slice: {key}")
            continue
        if key in seen_keys:
            issues.append(f"duplicate metric slice: {key}")
            continue
        seen_keys.add(key)
        reference = REFERENCE_BY_KEY[key]
        for field in VALUE_FIELDS:
            candidate = row.get(field, "")
            expected = reference[field]
            if candidate in (None, "") and expected == "":
                continue
            # validate-metrics should use the same final rounded month-level values
            # that the verifier recomputes, so near-miss display values are rejected
            # before submit-report is attempted.
            if float(candidate) != float(expected):
                issues.append(f"metric slice {key} field {field} does not match the accepted contract")
    return (not issues, issues)


def _validate_submission(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    required = {
        "manifest_id",
        "analysis_window",
        "metrics_validation_id",
        "metrics_snapshot",
        "diagnosis_report",
        "executive_summary_markdown",
    }
    missing = required - set(payload.keys())
    if missing:
        issues.append(f"missing keys: {sorted(missing)}")
        return False, issues

    if payload["manifest_id"] != MANIFEST_ID:
        issues.append("manifest_id does not match current manifest")

    issues.extend(_validate_submission_metrics_snapshot(payload["metrics_snapshot"]))

    metrics_ok, metric_issues = _validate_metric_rows(payload["metrics_snapshot"])
    if not metrics_ok:
        issues.extend(metric_issues[:10])

    diagnosis = payload["diagnosis_report"]
    diagnosis_required = {
        "analysis_window",
        "segments_evaluated",
        "channels_evaluated",
        "top_growth_drivers",
        "top_risk_drivers",
        "efficiency_findings",
        "retention_findings",
        "support_product_findings",
        "recommended_actions",
    }
    if not isinstance(diagnosis, dict):
        issues.append("diagnosis_report must be an object")
    else:
        missing_diag = diagnosis_required - set(diagnosis.keys())
        if missing_diag:
            issues.append(f"diagnosis_report missing keys: {sorted(missing_diag)}")
        ranked_lists = [
            "top_growth_drivers",
            "top_risk_drivers",
            "efficiency_findings",
            "retention_findings",
            "support_product_findings",
        ]
        for key in ranked_lists + ["recommended_actions"]:
            if not isinstance(diagnosis.get(key), list) or not diagnosis.get(key):
                issues.append(f"{key} must be a non-empty list")

        if diagnosis.get("analysis_window") != {
            "start_month": REQUIRED_DIMENSIONS["months"][0],
            "end_month": REQUIRED_DIMENSIONS["months"][-1],
        }:
            issues.append("diagnosis_report.analysis_window does not match the manifest window")
        if diagnosis.get("segments_evaluated") != REQUIRED_DIMENSIONS["segments"]:
            issues.append("diagnosis_report.segments_evaluated must match the manifest segments")
        if diagnosis.get("channels_evaluated") != REQUIRED_DIMENSIONS["channels"]:
            issues.append("diagnosis_report.channels_evaluated must match the manifest channels")

        if not issues:
            _validate_ranked_finding(
                "top_growth_drivers[0]",
                diagnosis["top_growth_drivers"][0],
                EXPECTED_INSIGHTS["growth"],
                issues,
                string_fields=["segment", "channel"],
                numeric_fields={
                    "healthy_growth_score": 0.05,
                    "q1_net_arr_delta": 0.05,
                    "q2_net_arr_delta": 0.05,
                    "delta_vs_baseline": 0.05,
                    "q2_revenue_retention_rate": 1e-4,
                    "q2_activation_rate": 1e-4,
                    "q2_payback_months": 0.05,
                },
            )
            _validate_ranked_finding(
                "top_risk_drivers[0]",
                diagnosis["top_risk_drivers"][0],
                EXPECTED_INSIGHTS["risk"],
                issues,
                string_fields=["segment", "channel", "focus_region"],
                numeric_fields={
                    "risk_score": 0.05,
                    "q2_net_arr_delta": 0.05,
                    "q2_revenue_retention_rate": 1e-4,
                    "q2_ticket_rate_per_100_accounts": 0.05,
                    "q2_refund_rate": 1e-4,
                    "q2_activation_rate": 1e-4,
                },
            )
            _validate_risk_chain(diagnosis["top_risk_drivers"][0], EXPECTED_INSIGHTS["risk"], issues)
            _validate_ranked_finding(
                "efficiency_findings[0]",
                diagnosis["efficiency_findings"][0],
                EXPECTED_INSIGHTS["efficiency"],
                issues,
                string_fields=["channel"],
                numeric_fields={
                    "efficiency_score": 0.05,
                    "q1_cac": 0.05,
                    "q2_cac": 0.05,
                    "q1_payback_months": 0.05,
                    "q2_payback_months": 0.05,
                    "q2_activation_rate": 1e-4,
                },
            )
            _validate_ranked_finding(
                "retention_findings[0]",
                diagnosis["retention_findings"][0],
                EXPECTED_INSIGHTS["retention"],
                issues,
                string_fields=["segment", "channel"],
                numeric_fields={
                    "retention_deterioration_score": 0.05,
                    "q1_logo_retention_rate": 1e-4,
                    "q2_logo_retention_rate": 1e-4,
                    "q1_revenue_retention_rate": 1e-4,
                    "q2_revenue_retention_rate": 1e-4,
                },
            )
            _validate_ranked_finding(
                "support_product_findings[0]",
                diagnosis["support_product_findings"][0],
                EXPECTED_INSIGHTS["support_product"],
                issues,
                string_fields=["segment", "channel", "region"],
                numeric_fields={
                    "support_product_score": 0.05,
                    "q2_ticket_rate_per_100_accounts": 0.05,
                    "q2_p1_response_sla_rate": 1e-4,
                    "q2_activation_rate": 1e-4,
                    "q2_pql_to_paid_rate": 1e-4,
                },
            )

        actions = diagnosis.get("recommended_actions", [])
        if len(actions) < 3 or any(len(str(action).strip()) < 20 for action in actions):
            issues.append("recommended_actions must contain at least three concrete actions")

    summary = str(payload["executive_summary_markdown"]).strip()
    if len(summary) < 250:
        issues.append("executive_summary_markdown is too short")
    if not summary.startswith("# "):
        issues.append("executive_summary_markdown must start with a level-1 markdown heading")
    lowered_summary = summary.lower()
    required_terms = [
        str(EXPECTED_INSIGHTS["growth"]["segment"]).lower(),
        str(EXPECTED_INSIGHTS["growth"]["channel"]).lower(),
        str(EXPECTED_INSIGHTS["risk"]["segment"]).lower(),
        str(EXPECTED_INSIGHTS["risk"]["channel"]).lower(),
        str(EXPECTED_INSIGHTS["risk"]["focus_region"]).lower(),
        str(EXPECTED_INSIGHTS["risk"]["break_month"]).lower(),
        str(EXPECTED_INSIGHTS["risk"]["control_slice"]["segment"]).lower(),
        str(EXPECTED_INSIGHTS["risk"]["control_slice"]["channel"]).lower(),
        str(EXPECTED_INSIGHTS["efficiency"]["channel"]).lower(),
    ]
    missing_terms = [term for term in required_terms if term not in lowered_summary]
    if missing_terms:
        issues.append("executive_summary_markdown must mention the leading quantified growth, risk, and efficiency findings")
    return (not issues, issues)


def _summarize_metric_issue_codes(issues: list[str]) -> list[str]:
    codes: set[str] = set()
    for issue in issues:
        if issue.startswith("expected ") and "metric rows" in issue:
            codes.add("E_METRIC_ROW_COUNT")
        elif issue.startswith("unexpected metric slice:"):
            codes.add("E_METRIC_SLICE_UNKNOWN")
        elif issue.startswith("duplicate metric slice:"):
            codes.add("E_METRIC_DUPLICATE")
        elif "missing field" in issue:
            codes.add("E_METRIC_SCHEMA")
        elif "must be a string" in issue:
            codes.add("E_METRIC_TYPE")
        elif "does not match the accepted contract" in issue:
            codes.add("E_METRIC_VALUE_MISMATCH")
        else:
            codes.add("E_METRIC_CONTRACT")
    return sorted(codes)


def _summarize_submission_issue_codes(issues: list[str]) -> list[str]:
    codes: set[str] = set()
    for issue in issues:
        if issue.startswith("missing keys:"):
            codes.add("E_SUBMISSION_SCHEMA")
        elif issue.startswith("manifest_id does not match"):
            codes.add("E_MANIFEST_MISMATCH")
        elif issue.startswith("metrics_validation_id does not match"):
            codes.add("E_VALIDATION_LINK")
        elif issue.startswith("metrics_snapshot") or issue.startswith("metric slice "):
            codes.add("E_METRICS_BUNDLE")
        elif issue.startswith("diagnosis_report missing keys:"):
            codes.add("E_DIAGNOSIS_SCHEMA")
        elif issue.startswith("diagnosis_report."):
            codes.add("E_DIAGNOSIS_SCHEMA")
        elif issue.startswith("top_growth_drivers[0]"):
            codes.add("E_GROWTH_DRIVER_MISMATCH")
        elif issue.startswith("top_risk_drivers[0]"):
            codes.add("E_RISK_DRIVER_MISMATCH")
        elif issue.startswith("efficiency_findings[0]"):
            codes.add("E_EFFICIENCY_MISMATCH")
        elif issue.startswith("retention_findings[0]"):
            codes.add("E_RETENTION_MISMATCH")
        elif issue.startswith("support_product_findings[0]"):
            codes.add("E_SUPPORT_PRODUCT_MISMATCH")
        elif issue.startswith("recommended_actions"):
            codes.add("E_RECOMMENDED_ACTIONS")
        elif issue.startswith("executive_summary_markdown"):
            codes.add("E_SUMMARY_CONTENT")
        elif "non-empty list" in issue:
            codes.add("E_DIAGNOSIS_SCHEMA")
        else:
            codes.add("E_SUBMISSION_CONTRACT")
    return sorted(codes)


def _build_helper_diagnosis_reference() -> dict[str, Any]:
    return {
        "top_growth_drivers_first_item": {
            "rank": 1,
            **EXPECTED_INSIGHTS["growth"],
            "evidence": (
                f"Q2 net ARR for {EXPECTED_INSIGHTS['growth']['segment']} via "
                f"{EXPECTED_INSIGHTS['growth']['channel']} reached "
                f"{EXPECTED_INSIGHTS['growth']['q2_net_arr_delta']:.2f} versus "
                f"{EXPECTED_INSIGHTS['growth']['q1_net_arr_delta']:.2f} in Q1, "
                f"with {EXPECTED_INSIGHTS['growth']['q2_revenue_retention_rate']:.4f} "
                f"revenue retention, {EXPECTED_INSIGHTS['growth']['q2_activation_rate']:.4f} activation, "
                f"and {EXPECTED_INSIGHTS['growth']['q2_payback_months']:.2f} months payback."
            ),
        },
        "top_risk_drivers_first_item": {
            "rank": 1,
            **EXPECTED_INSIGHTS["risk"],
            "evidence": (
                f"{EXPECTED_INSIGHTS['risk']['segment']} via {EXPECTED_INSIGHTS['risk']['channel']} "
                f"broke in {EXPECTED_INSIGHTS['risk']['break_month']}: Q2 net ARR was "
                f"{EXPECTED_INSIGHTS['risk']['q2_net_arr_delta']:.2f}, revenue retention averaged "
                f"{EXPECTED_INSIGHTS['risk']['q2_revenue_retention_rate']:.4f}, and the focus region "
                f"{EXPECTED_INSIGHTS['risk']['focus_region']} drove "
                f"{EXPECTED_INSIGHTS['risk']['focus_region_refund_share']:.4f} of refunds with "
                f"{EXPECTED_INSIGHTS['risk']['q2_ticket_rate_per_100_accounts']:.2f} tickets per 100 accounts. "
                f"Control slice {EXPECTED_INSIGHTS['risk']['control_slice']['segment']}/"
                f"{EXPECTED_INSIGHTS['risk']['control_slice']['channel']} stayed positive."
            ),
        },
        "efficiency_findings_first_item": {
            "rank": 1,
            **EXPECTED_INSIGHTS["efficiency"],
            "evidence": (
                f"{EXPECTED_INSIGHTS['efficiency']['channel']} averaged Q2 CAC of "
                f"{EXPECTED_INSIGHTS['efficiency']['q2_cac']:.2f}, Q2 payback of "
                f"{EXPECTED_INSIGHTS['efficiency']['q2_payback_months']:.2f} months, "
                f"and {EXPECTED_INSIGHTS['efficiency']['q2_activation_rate']:.4f} activation "
                f"after segment averaging."
            ),
        },
        "retention_findings_first_item": {
            "rank": 1,
            **EXPECTED_INSIGHTS["retention"],
            "evidence": (
                f"{EXPECTED_INSIGHTS['retention']['segment']} via {EXPECTED_INSIGHTS['retention']['channel']} "
                f"saw logo retention move from {EXPECTED_INSIGHTS['retention']['q1_logo_retention_rate']:.4f} "
                f"in Q1 to {EXPECTED_INSIGHTS['retention']['q2_logo_retention_rate']:.4f} in Q2, while "
                f"revenue retention moved from {EXPECTED_INSIGHTS['retention']['q1_revenue_retention_rate']:.4f} "
                f"to {EXPECTED_INSIGHTS['retention']['q2_revenue_retention_rate']:.4f}."
            ),
        },
        "support_product_findings_first_item": {
            "rank": 1,
            **EXPECTED_INSIGHTS["support_product"],
            "evidence": (
                f"{EXPECTED_INSIGHTS['support_product']['region']} in "
                f"{EXPECTED_INSIGHTS['support_product']['segment']} / "
                f"{EXPECTED_INSIGHTS['support_product']['channel']} reached "
                f"{EXPECTED_INSIGHTS['support_product']['q2_ticket_rate_per_100_accounts']:.2f} tickets per 100 accounts, "
                f"{EXPECTED_INSIGHTS['support_product']['q2_p1_response_sla_rate']:.4f} P1 SLA attainment, "
                f"{EXPECTED_INSIGHTS['support_product']['q2_activation_rate']:.4f} activation, and "
                f"{EXPECTED_INSIGHTS['support_product']['q2_pql_to_paid_rate']:.4f} PQL-to-paid conversion in Q2."
            ),
        },
        "summary_required_mentions": [
            EXPECTED_INSIGHTS["growth"]["segment"],
            EXPECTED_INSIGHTS["growth"]["channel"],
            EXPECTED_INSIGHTS["risk"]["segment"],
            EXPECTED_INSIGHTS["risk"]["channel"],
            EXPECTED_INSIGHTS["risk"]["focus_region"],
            EXPECTED_INSIGHTS["risk"]["break_month"],
            EXPECTED_INSIGHTS["risk"]["control_slice"]["segment"],
            EXPECTED_INSIGHTS["risk"]["control_slice"]["channel"],
            EXPECTED_INSIGHTS["efficiency"]["channel"],
        ],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BoardAudit/1.0"

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else b"{}"
        return json.loads(data.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"ok": True, "service": "board-audit"})
            return
        if self.path == "/manifest":
            payload = {
                "manifest_id": MANIFEST_ID,
                "analysis_window": {
                    "start_month": REQUIRED_DIMENSIONS["months"][0],
                    "end_month": REQUIRED_DIMENSIONS["months"][-1],
                },
                "segments": REQUIRED_DIMENSIONS["segments"],
                "channels": REQUIRED_DIMENSIONS["channels"],
                "expected_metric_rows": len(REFERENCE_METRICS),
            }
            helper_scripts = _available_helper_scripts()
            if helper_scripts:
                payload["optional_helper_scripts"] = helper_scripts
                payload["optional_helper_workflow"] = [
                    "probe_metric_contract.py",
                    "recompute_metrics_diff.py",
                    "scan_growth_signals.py",
                    "package_and_submit_bundle.py",
                ]
                payload["required_metric_fields"] = KEY_FIELDS + VALUE_FIELDS
                payload["submission_schema_version"] = "1.1"
                payload["metric_implementation_notes"] = HELPER_METRIC_IMPLEMENTATION_NOTES
                payload["metric_validation_rule"] = (
                    "validate-metrics accepts only the final rounded month-level values from the metric contract; "
                    "near-miss display values that differ by 0.01 or 0.0001 still fail validation."
                )
                payload["final_submission_contract"] = {
                    "metrics_snapshot_source": "must be re-read from /app/output/metrics_snapshot.csv using standard CSV semantics",
                    "metrics_snapshot_value_type": "all metric cell values must be strings in the final bundle",
                    "bundle_value_types": "final_submission.json must contain JSON-serializable base types only",
                }
                payload["diagnosis_contract"] = {
                    "risk_evidence_chain": "top_risk_drivers[0] must include break_month, focus_region_refund_share, a Q2 monthly_signal_chain, and a same-segment control_slice",
                }
                payload["diagnosis_required_fields"] = {
                    "top_level": [
                        "analysis_window",
                        "segments_evaluated",
                        "channels_evaluated",
                        "top_growth_drivers",
                        "top_risk_drivers",
                        "efficiency_findings",
                        "retention_findings",
                        "support_product_findings",
                        "recommended_actions",
                    ],
                    "top_growth_drivers_first_item": [
                        "rank",
                        "segment",
                        "channel",
                        "healthy_growth_score",
                        "q1_net_arr_delta",
                        "q2_net_arr_delta",
                        "delta_vs_baseline",
                        "q2_revenue_retention_rate",
                        "q2_activation_rate",
                        "q2_payback_months",
                        "evidence",
                    ],
                    "top_risk_drivers_first_item": [
                        "rank",
                        "segment",
                        "channel",
                        "risk_score",
                        "break_month",
                        "q2_net_arr_delta",
                        "q2_revenue_retention_rate",
                        "q2_ticket_rate_per_100_accounts",
                        "q2_refund_rate",
                        "q2_activation_rate",
                        "focus_region",
                        "focus_region_refund_share",
                        "monthly_signal_chain",
                        "control_slice",
                        "evidence",
                    ],
                    "efficiency_findings_first_item": [
                        "rank",
                        "channel",
                        "efficiency_score",
                        "q1_cac",
                        "q2_cac",
                        "q1_payback_months",
                        "q2_payback_months",
                        "q2_activation_rate",
                        "evidence",
                    ],
                    "retention_findings_first_item": [
                        "rank",
                        "segment",
                        "channel",
                        "retention_deterioration_score",
                        "q1_logo_retention_rate",
                        "q2_logo_retention_rate",
                        "q1_revenue_retention_rate",
                        "q2_revenue_retention_rate",
                        "evidence",
                    ],
                    "support_product_findings_first_item": [
                        "rank",
                        "segment",
                        "channel",
                        "region",
                        "support_product_score",
                        "q2_ticket_rate_per_100_accounts",
                        "q2_p1_response_sla_rate",
                        "q2_activation_rate",
                        "q2_pql_to_paid_rate",
                        "evidence",
                    ],
                }
                payload["diagnosis_field_notes"] = {
                    "ranked_list_scope": "The first item in each ranked list is audited most strictly; keep field names and value types stable.",
                    "evidence_requirement": "Each first-ranked finding should include an evidence string of at least 40 characters.",
                    "quarter_aggregation_rule": "When a diagnosis formula references q1/q2 metrics, use the simple arithmetic mean of the monthly metrics_snapshot rows for that period and slice unless the field is explicitly defined at region level.",
                    "score_precision_rule": "For healthy_growth_score, risk_score, retention_deterioration_score, efficiency_score, and support_product_score, compute the score from the underlying quarter aggregates first and only round the final score to 2 decimals; do not recompute the score from already rounded display fields.",
                    "break_month_rule": "For top_risk_drivers[0], break_month is the earliest Q2 month where net_arr_delta < 0.0 or revenue_retention_rate < 0.9.",
                    "monthly_signal_chain_schema": "top_risk_drivers[0].monthly_signal_chain must contain exactly the three Q2 checkpoints with month, net_arr_delta, revenue_retention_rate, ticket_rate_per_100_accounts, and activation_rate, all taken from the slice-level monthly metrics_snapshot rows for the winning segment/channel.",
                    "control_slice_schema": "top_risk_drivers[0].control_slice must stay in the same segment, switch to a different positive-Q2 channel, and include segment, channel, q2_net_arr_delta, q2_revenue_retention_rate, and q2_ticket_rate_per_100_accounts.",
                    "control_slice_aggregation_rule": "top_risk_drivers[0].control_slice.q2_revenue_retention_rate and q2_ticket_rate_per_100_accounts should come from the Q2 mean of that control slice's monthly metrics_snapshot rows.",
                    "risk_region_metric_scope": "For top_risk_drivers[0], the top-level q2_ticket_rate_per_100_accounts, q2_refund_rate, and q2_activation_rate are focus_region values; q2_net_arr_delta and q2_revenue_retention_rate remain segment/channel slice values; monthly_signal_chain stays slice-level.",
                    "risk_region_aggregation_rule": "For top_risk_drivers[0], focus_region q2_ticket_rate_per_100_accounts must be computed from total Q2 tickets_opened divided by total Q2 active_accounts in that region (then *100), not by averaging monthly rates. q2_refund_rate should similarly use total Q2 refund_usd / total Q2 gross_usd for the focus_region.",
                    "risk_region_aggregation_example": "Example pattern: if Q2 regional monthly ticket rates are 180.00, 360.00, and 400.00, do not average them. Recompute from summed Q2 tickets_opened and summed Q2 active_accounts for that region.",
                    "growth_metric_scope": "For top_growth_drivers[0], q1_net_arr_delta and q2_net_arr_delta are quarter sums, while q2_revenue_retention_rate, q2_activation_rate, and q2_payback_months are Q2 means from the winning slice's monthly metrics_snapshot rows.",
                    "efficiency_metric_scope": "For efficiency_findings, first compute each segment x channel slice's q1/q2 CAC, q1/q2 payback, and Q2 activation from that slice's monthly metrics_snapshot rows; then aggregate by taking the simple mean of those three segment-level quarter summaries for the channel. Do not weight by months, logos, or spend, and do not recompute from raw channel-wide totals.",
                    "efficiency_score_rule": "efficiency_score must be computed from the underlying unrounded aggregated channel values, and only the final score should be rounded to 2 decimals. Do not multiply the already rounded display fields back together.",
                    "support_product_scope": "support_product_findings are ranked at the Q2 region-within-segment/channel slice, not just at the segment/channel aggregate.",
                    "support_product_aggregation_rule": "For support_product_findings, q2_ticket_rate_per_100_accounts, q2_refund_rate, q2_activation_rate, q2_p1_response_sla_rate, and q2_pql_to_paid_rate should all be computed from total Q2 region-level numerators and denominators before scoring; support_product_score is then computed from those unrounded aggregated values and rounded at the end.",
                    "support_product_formula_note": "support_product_score = q2_ticket_rate_per_100_accounts + q2_refund_rate * 1000.0 + max(0.0, 1.0 - q2_activation_rate) * 100.0 + max(0.0, 1.0 - q2_p1_response_sla_rate) * 100.0, using the unrounded Q2 region aggregates before the final 2-decimal round.",
                    "recommended_actions_rule": "recommended_actions must contain at least three concrete action strings, each at least 20 characters long.",
                }
                payload["summary_contract"] = {
                    "min_length": 250,
                    "heading_format": "executive_summary.md must start with a level-1 markdown heading like '# 2025 H1 Board Summary' before the prose body",
                    "required_mentions": [
                        "top_growth_drivers[0].segment",
                        "top_growth_drivers[0].channel",
                        "top_risk_drivers[0].segment",
                        "top_risk_drivers[0].channel",
                        "top_risk_drivers[0].focus_region",
                        "top_risk_drivers[0].break_month",
                        "top_risk_drivers[0].control_slice.segment",
                        "top_risk_drivers[0].control_slice.channel",
                        "efficiency_findings[0].channel",
                    ],
                    "note": "The executive summary should explicitly mention the leading quantified growth, risk, and efficiency winners taken from the final diagnosis payload, and it should remain a board-ready markdown document rather than plain prose.",
                }
                payload["diagnosis_scoring_reference"] = {
                    "top_growth_drivers": {
                        "ranking": "maximize healthy_growth_score, then q2_net_arr_delta",
                        "formula": "q2_net_arr_delta * max(q2_revenue_retention_rate, 0.0) * max(q2_activation_rate, 0.05) / max(q2_payback_months or 999.0, 1.0)",
                    },
                    "top_risk_drivers": {
                        "ranking": "maximize risk_score, then most negative q2_net_arr_delta",
                        "formula": "max(0.0, -q2_net_arr_delta) * 2.0 + max(0.0, 1.0 - q2_revenue_retention_rate) * 50000.0 + max(0.0, 1.0 - q2_logo_retention_rate) * 25000.0 + q2_ticket_rate_per_100_accounts * 50.0 + max(0.0, q2_payback_months - 12.0) * 1000.0",
                        "focus_region_rule": "within the chosen segment/channel, pick the Q2 region maximizing (refund_rate, ticket_rate, -activation_rate)",
                        "control_slice_rule": "same segment, different channel, positive q2_net_arr_delta, then maximize (q2_revenue_retention_rate, q2_net_arr_delta, -q2_ticket_rate_per_100_accounts)",
                    },
                    "retention_findings": {
                        "ranking": "maximize retention_deterioration_score, then risk_score",
                        "formula": "max(0.0, q1_logo_retention_rate - q2_logo_retention_rate) * 100.0 + max(0.0, q1_revenue_retention_rate - q2_revenue_retention_rate) * 100.0",
                    },
                    "efficiency_findings": {
                        "aggregation": "aggregate by channel across segments using mean q1/q2 CAC, payback, and q2 activation",
                        "formula": "q2_cac * max(q2_payback_months, 1.0) / max(q2_activation_rate, 0.05)",
                    },
                    "support_product_findings": {
                        "ranking": "maximize support_product_score, then q2_refund_rate",
                        "formula": "q2_ticket_rate_per_100_accounts + q2_refund_rate * 1000.0 + max(0.0, 1.0 - q2_activation_rate) * 100.0 + max(0.0, 1.0 - q2_p1_response_sla_rate) * 100.0",
                    },
                }
                payload["helper_submission_workflow"] = {
                    "note": (
                        "When helper probes are present, validate-metrics returns an audited diagnosis "
                        "reference preview for the first-ranked findings. Use those exact values when you "
                        "assemble diagnosis_report.json and the executive summary."
                    ),
                    "preview_source": "POST /validate-metrics on an accepted metrics_snapshot",
                }
            _append_trace("manifest", {"manifest_id": MANIFEST_ID})
            self._send_json(payload)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/validate-metrics":
            global LAST_VALIDATION_RECORD
            payload = self._read_json()
            rows = payload.get("metrics", [])
            accepted, issues = _validate_metric_rows(rows)
            validation_id = f"metrics-{uuid.uuid4().hex[:10]}"
            error_codes = _summarize_metric_issue_codes(issues)
            response = {
                "accepted": accepted,
                "validation_id": validation_id,
                "status": "accepted" if accepted else "rejected",
            }
            if accepted and _helper_mode_enabled():
                response["audited_diagnosis_reference"] = _build_helper_diagnosis_reference()
            if not accepted:
                response["issue_count"] = len(issues)
                response["error_codes"] = error_codes
            LAST_VALIDATION_RECORD = {
                "response": response,
                "row_count": len(rows),
                "issues": issues,
            }
            _append_trace(
                "validate-metrics",
                {
                    "validation_id": validation_id,
                    "accepted": accepted,
                    "row_count": len(rows),
                    "error_codes": error_codes,
                },
            )
            self._send_json(response, status=200 if accepted else 409)
            return

        if self.path == "/submit-report":
            global LAST_SUBMISSION_RECORD
            payload = self._read_json()
            accepted, issues = _validate_submission(payload)
            canonical_hash = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
            report_id = f"report-{uuid.uuid4().hex[:12]}"

            last_validation_id = ""
            if LAST_VALIDATION_RECORD is not None:
                last_validation_id = str(LAST_VALIDATION_RECORD.get("response", {}).get("validation_id", ""))

            if payload.get("metrics_validation_id") != last_validation_id:
                issues.append("metrics_validation_id does not match the latest live validation result")
                accepted = False

            error_codes = _summarize_submission_issue_codes(issues)
            receipt = {
                "accepted": accepted,
                "report_id": report_id,
                "request_sha256": canonical_hash,
                "validated_metrics": payload.get("metrics_validation_id", ""),
                "status": "accepted" if accepted else "rejected",
            }
            if not accepted:
                receipt["issue_count"] = len(issues)
                receipt["error_codes"] = error_codes
                if _helper_mode_enabled():
                    receipt["mismatch_details"] = issues[:8]
            LAST_SUBMISSION_RECORD = {
                "receipt": receipt,
                "payload_sha256": canonical_hash,
                "payload": payload,
                "issues": issues,
            }
            _append_trace(
                "submit-report",
                {
                    "accepted": accepted,
                    "report_id": report_id,
                    "payload_sha256": canonical_hash,
                    "error_codes": error_codes,
                },
            )
            self._send_json(receipt, status=200 if accepted else 409)
            return

        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
