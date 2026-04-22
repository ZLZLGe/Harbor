#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests


ROOT = Path(os.environ.get("BOARD_DATA_ROOT", "/app/data"))
OUTPUT_ROOT = Path(os.environ.get("BOARD_OUTPUT_ROOT", "/app/output"))
API_URL = os.environ.get("AUDIT_API_URL", "http://127.0.0.1:8321")
SERVER_PATH = Path(os.environ.get("BOARD_AUDIT_SERVER_PATH", "/services/board-audit/server.py"))
MONTHS = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
CHANNELS = ["Organic", "Paid Search", "Paid Social", "Partner"]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ensure_audit_service() -> None:
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.ok:
            return
    except requests.RequestException:
        pass

    subprocess.Popen(
        [sys.executable, str(SERVER_PATH)],
        stdout=open("/tmp/board-audit-solution.log", "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            response = requests.get(f"{API_URL}/health", timeout=2)
            if response.ok:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("board-audit service did not become healthy")


def compute_metrics() -> list[dict]:
    subscriptions = read_csv_rows(ROOT / "subscriptions" / "account_month_status.csv")
    usage = read_csv_rows(ROOT / "product" / "usage_monthly.csv")
    tickets = read_csv_rows(ROOT / "support" / "tickets.csv")
    spend = read_csv_rows(ROOT / "marketing" / "channel_spend.csv")
    spend_map = {(row["month"], row["channel"]): float(row["spend_usd"]) for row in spend}

    rows: list[dict] = []
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
                    avg_new_arr = new_arr / new_paid_count
                    payback = cac / ((avg_new_arr / 12.0) * 0.82)
                    cac_value = f"{cac:.2f}"
                    payback_value = f"{payback:.2f}"

                rows.append(
                    {
                        "month": month,
                        "segment": segment,
                        "channel": channel,
                        "new_arr": f"{new_arr:.2f}",
                        "expansion_arr": f"{expansion_arr:.2f}",
                        "contraction_arr": f"{contraction_arr:.2f}",
                        "churned_arr": f"{churned_arr:.2f}",
                        "net_arr_delta": f"{(new_arr + expansion_arr - contraction_arr - churned_arr):.2f}",
                        "mrr": f"{(end_arr_total / 12.0):.2f}",
                        "logo_retention_rate": f"{((len(retained) / len(start_active)) if start_active else 1.0):.4f}",
                        "revenue_retention_rate": f"{((retained_end_arr / start_arr) if start_arr else 1.0):.4f}",
                        "cac": cac_value,
                        "payback_months": payback_value,
                        "activation_rate": f"{((activated_count / new_paid_count) if new_paid_count else 1.0):.4f}",
                        "pql_to_paid_rate": f"{((pql_paid / pql_total) if pql_total else 0.0):.4f}",
                        "ticket_rate_per_100_accounts": f"{((ticket_count / active_accounts * 100.0) if active_accounts else 0.0):.2f}",
                        "p1_response_sla_rate": f"{((p1_met / p1_total) if p1_total else 1.0):.4f}",
                    }
                )
    return rows


def _to_float(value: str) -> float:
    if value == "":
        return 0.0
    return float(value)


def _average_metric(rows: list[dict], field: str, digits: int) -> float:
    values = [_to_float(row[field]) for row in rows if row.get(field, "") != ""]
    if not values:
        return 0.0
    return round(sum(values) / len(values), digits)


def _build_monthly_slice_metrics(metrics: list[dict]) -> dict[tuple[str, str, str], dict]:
    return {
        (row["segment"], row["channel"], row["month"]): {
            "month": row["month"],
            "segment": row["segment"],
            "channel": row["channel"],
            "net_arr_delta": round(_to_float(row["net_arr_delta"]), 2),
            "revenue_retention_rate": round(_to_float(row["revenue_retention_rate"]), 4),
            "ticket_rate_per_100_accounts": round(_to_float(row["ticket_rate_per_100_accounts"]), 2),
            "activation_rate": round(_to_float(row["activation_rate"]), 4),
        }
        for row in metrics
    }


def compute_expected_insights(metrics: list[dict]) -> dict:
    subscriptions = read_csv_rows(ROOT / "subscriptions" / "account_month_status.csv")
    usage = read_csv_rows(ROOT / "product" / "usage_monthly.csv")
    tickets = read_csv_rows(ROOT / "support" / "tickets.csv")
    invoices = read_csv_rows(ROOT / "orders" / "invoices.csv")
    q1_months = set(MONTHS[:3])
    q2_months = set(MONTHS[3:])
    monthly_slice_metrics = _build_monthly_slice_metrics(metrics)

    slice_metrics: dict[tuple[str, str], dict] = {}
    for segment in SEGMENTS:
        for channel in CHANNELS:
            metric_rows = [row for row in metrics if row["segment"] == segment and row["channel"] == channel]
            q1_rows = [row for row in metric_rows if row["month"] in q1_months]
            q2_rows = [row for row in metric_rows if row["month"] in q2_months]
            q1_cac = _average_metric(q1_rows, "cac", 2)
            q2_cac = _average_metric(q2_rows, "cac", 2)
            q1_payback = _average_metric(q1_rows, "payback_months", 2)
            q2_payback = _average_metric(q2_rows, "payback_months", 2)
            q1_net_arr = round(sum(_to_float(row["net_arr_delta"]) for row in q1_rows), 2)
            q2_net_arr = round(sum(_to_float(row["net_arr_delta"]) for row in q2_rows), 2)
            q1_logo_retention = _average_metric(q1_rows, "logo_retention_rate", 4)
            q2_logo_retention = _average_metric(q2_rows, "logo_retention_rate", 4)
            q1_revenue_retention = _average_metric(q1_rows, "revenue_retention_rate", 4)
            q2_revenue_retention = _average_metric(q2_rows, "revenue_retention_rate", 4)
            q2_activation = _average_metric(q2_rows, "activation_rate", 4)
            q2_ticket_rate = _average_metric(q2_rows, "ticket_rate_per_100_accounts", 2)

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

    region_signals = defaultdict(
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

    region_summary = {}
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
        region_summary[key] = {
            "segment": key[0],
            "channel": key[1],
            "region": key[2],
            "q2_refund_rate": round(refund_rate, 4),
            "q2_ticket_rate_per_100_accounts": round(ticket_rate, 2),
            "q2_p1_response_sla_rate": round(sla_rate, 4),
            "q2_activation_rate": round(activation_rate, 4),
            "q2_pql_to_paid_rate": round(pql_to_paid_rate, 4),
            "support_product_score": round(
                ticket_rate
                + refund_rate * 1000.0
                + max(0.0, 1.0 - activation_rate) * 100.0
                + max(0.0, 1.0 - sla_rate) * 100.0,
                2,
            ),
        }

    channel_summary = {}
    for channel in CHANNELS:
        relevant = [value for value in slice_metrics.values() if value["channel"] == channel]
        q2_activation = round(sum(float(row["q2_activation_rate"]) for row in relevant) / len(relevant), 4)
        q1_cac = round(sum(float(row["q1_cac"]) for row in relevant) / len(relevant), 2)
        q2_cac = round(sum(float(row["q2_cac"]) for row in relevant) / len(relevant), 2)
        q1_payback = round(sum(float(row["q1_payback_months"]) for row in relevant) / len(relevant), 2)
        q2_payback = round(sum(float(row["q2_payback_months"]) for row in relevant) / len(relevant), 2)
        channel_summary[channel] = {
            "channel": channel,
            "q1_cac": q1_cac,
            "q2_cac": q2_cac,
            "q1_payback_months": q1_payback,
            "q2_payback_months": q2_payback,
            "q2_activation_rate": q2_activation,
            "efficiency_score": round(q2_cac * max(q2_payback, 1.0) / max(q2_activation, 0.05), 2),
        }

    growth = max(slice_metrics.values(), key=lambda row: (row["healthy_growth_score"], row["q2_net_arr_delta"]))
    risk = max(slice_metrics.values(), key=lambda row: (row["risk_score"], -row["q2_net_arr_delta"]))
    retention = max(slice_metrics.values(), key=lambda row: (row["retention_deterioration_score"], row["risk_score"]))
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
        for month in MONTHS[3:]
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


def build_diagnosis(metrics: list[dict]) -> tuple[dict, dict]:
    insights = compute_expected_insights(metrics)
    growth = insights["growth"]
    risk = insights["risk"]
    efficiency = insights["efficiency"]
    retention = insights["retention"]
    support_product = insights["support_product"]

    diagnosis = {
        "analysis_window": {"start_month": "2025-01", "end_month": "2025-06"},
        "segments_evaluated": SEGMENTS,
        "channels_evaluated": CHANNELS,
        "top_growth_drivers": [
            {
                "segment": growth["segment"],
                "channel": growth["channel"],
                "healthy_growth_score": growth["healthy_growth_score"],
                "q1_net_arr_delta": growth["q1_net_arr_delta"],
                "q2_net_arr_delta": growth["q2_net_arr_delta"],
                "delta_vs_baseline": growth["delta_vs_baseline"],
                "q2_revenue_retention_rate": growth["q2_revenue_retention_rate"],
                "q2_activation_rate": growth["q2_activation_rate"],
                "q2_payback_months": growth["q2_payback_months"],
                "evidence": (
                    f"{growth['segment']} / {growth['channel']} posts the strongest healthy-growth score at "
                    f"{growth['healthy_growth_score']:.2f}, with Q2 net ARR delta {growth['q2_net_arr_delta']:.2f} "
                    f"versus {growth['q1_net_arr_delta']:.2f} in Q1, while revenue retention stays at "
                    f"{growth['q2_revenue_retention_rate']:.4f} and activation at {growth['q2_activation_rate']:.4f}."
                ),
            }
        ],
        "top_risk_drivers": [
            {
                "segment": risk["segment"],
                "channel": risk["channel"],
                "focus_region": risk["focus_region"],
                "risk_score": risk["risk_score"],
                "q2_net_arr_delta": risk["q2_net_arr_delta"],
                "q2_revenue_retention_rate": risk["q2_revenue_retention_rate"],
                "q2_ticket_rate_per_100_accounts": risk["q2_ticket_rate_per_100_accounts"],
                "q2_refund_rate": risk["q2_refund_rate"],
                "q2_activation_rate": risk["q2_activation_rate"],
                "focus_region_refund_share": risk["focus_region_refund_share"],
                "break_month": risk["break_month"],
                "monthly_signal_chain": risk["monthly_signal_chain"],
                "control_slice": risk["control_slice"],
                "evidence": (
                    f"{risk['segment']} / {risk['channel']} is the highest-risk slice with score {risk['risk_score']:.2f}. "
                    f"The break starts in {risk['break_month']}, Q2 net ARR delta falls to {risk['q2_net_arr_delta']:.2f}, "
                    f"revenue retention slips to {risk['q2_revenue_retention_rate']:.4f}, and {risk['focus_region']} accounts "
                    f"for {risk['focus_region_refund_share']:.4f} of slice refunds. The same-segment control is "
                    f"{risk['control_slice']['segment']} / {risk['control_slice']['channel']}, which still posts "
                    f"{risk['control_slice']['q2_net_arr_delta']:.2f} net ARR delta."
                ),
            }
        ],
        "efficiency_findings": [
            {
                "channel": efficiency["channel"],
                "efficiency_score": efficiency["efficiency_score"],
                "q1_cac": efficiency["q1_cac"],
                "q2_cac": efficiency["q2_cac"],
                "q1_payback_months": efficiency["q1_payback_months"],
                "q2_payback_months": efficiency["q2_payback_months"],
                "q2_activation_rate": efficiency["q2_activation_rate"],
                "evidence": (
                    f"{efficiency['channel']} is the weakest scaled acquisition lane, with efficiency score "
                    f"{efficiency['efficiency_score']:.2f}. CAC moves from {efficiency['q1_cac']:.2f} in Q1 to "
                    f"{efficiency['q2_cac']:.2f} in Q2, while payback sits at {efficiency['q2_payback_months']:.2f} "
                    f"months and activation averages {efficiency['q2_activation_rate']:.4f}."
                ),
            }
        ],
        "retention_findings": [
            {
                "segment": retention["segment"],
                "channel": retention["channel"],
                "retention_deterioration_score": retention["retention_deterioration_score"],
                "q1_logo_retention_rate": retention["q1_logo_retention_rate"],
                "q2_logo_retention_rate": retention["q2_logo_retention_rate"],
                "q1_revenue_retention_rate": retention["q1_revenue_retention_rate"],
                "q2_revenue_retention_rate": retention["q2_revenue_retention_rate"],
                "evidence": (
                    f"{retention['segment']} / {retention['channel']} shows the sharpest retention deterioration, with "
                    f"logo retention moving from {retention['q1_logo_retention_rate']:.4f} to {retention['q2_logo_retention_rate']:.4f} "
                    f"and revenue retention moving from {retention['q1_revenue_retention_rate']:.4f} to "
                    f"{retention['q2_revenue_retention_rate']:.4f}."
                ),
            }
        ],
        "support_product_findings": [
            {
                "segment": support_product["segment"],
                "channel": support_product["channel"],
                "region": support_product["region"],
                "support_product_score": support_product["support_product_score"],
                "q2_ticket_rate_per_100_accounts": support_product["q2_ticket_rate_per_100_accounts"],
                "q2_p1_response_sla_rate": support_product["q2_p1_response_sla_rate"],
                "q2_activation_rate": support_product["q2_activation_rate"],
                "q2_pql_to_paid_rate": support_product["q2_pql_to_paid_rate"],
                "evidence": (
                    f"{support_product['segment']} / {support_product['channel']} in {support_product['region']} carries the highest "
                    f"support-product stress score at {support_product['support_product_score']:.2f}, with ticket rate "
                    f"{support_product['q2_ticket_rate_per_100_accounts']:.2f}, P1 SLA {support_product['q2_p1_response_sla_rate']:.4f}, "
                    f"activation {support_product['q2_activation_rate']:.4f}, and PQL-to-paid {support_product['q2_pql_to_paid_rate']:.4f}."
                ),
            }
        ],
        "recommended_actions": [
            (
                f"Protect the healthiest scaled growth lane by leaning harder into {growth['segment']} / {growth['channel']}, "
                f"where Q2 net ARR delta reached {growth['q2_net_arr_delta']:.2f} with durable retention and activation."
            ),
            (
                f"Launch a recovery plan for {risk['focus_region']} within {risk['segment']} / {risk['channel']}: "
                f"refunds are {risk['q2_refund_rate']:.4f} of billed volume and ticket burden is "
                f"{risk['q2_ticket_rate_per_100_accounts']:.2f} per 100 active accounts."
            ),
            (
                f"Re-baseline acquisition guardrails for {efficiency['channel']} until CAC and payback improve from "
                f"{efficiency['q2_cac']:.2f} and {efficiency['q2_payback_months']:.2f} months, respectively."
            ),
        ],
    }
    return diagnosis, insights


def build_summary(insights: dict) -> str:
    growth = insights["growth"]
    risk = insights["risk"]
    efficiency = insights["efficiency"]
    support_product = insights["support_product"]
    retention = insights["retention"]
    return f"""# Board Growth Diagnostics Summary

## Executive takeaway

The healthiest scaled growth lane in 2025 H1 is **{growth['segment']} / {growth['channel']}**. Its Q2 net ARR delta reached **{growth['q2_net_arr_delta']:.2f}**, up from **{growth['q1_net_arr_delta']:.2f}** in Q1, while revenue retention held at **{growth['q2_revenue_retention_rate']:.4f}** and activation stayed at **{growth['q2_activation_rate']:.4f}**.

## Primary risk

The most important board-level risk is **{risk['segment']} / {risk['channel']}**, especially in **{risk['focus_region']}**. That slice posted a Q2 net ARR delta of **{risk['q2_net_arr_delta']:.2f}**, revenue retention of **{risk['q2_revenue_retention_rate']:.4f}**, refund rate of **{risk['q2_refund_rate']:.4f}**, and ticket burden of **{risk['q2_ticket_rate_per_100_accounts']:.2f}** per 100 active accounts.

The deterioration becomes visible in **{risk['break_month']}**, when the monthly signal chain starts to break across net ARR, retention, and support load. This is not a universal SMB issue: the control slice **{risk['control_slice']['segment']} / {risk['control_slice']['channel']}** still delivers **{risk['control_slice']['q2_net_arr_delta']:.2f}** Q2 net ARR delta with **{risk['control_slice']['q2_revenue_retention_rate']:.4f}** revenue retention.

## Efficiency and execution

Across acquisition channels, **{efficiency['channel']}** is the weakest efficiency lane. Q2 CAC sits at **{efficiency['q2_cac']:.2f}** versus **{efficiency['q1_cac']:.2f}** in Q1, and payback is **{efficiency['q2_payback_months']:.2f}** months with average activation of **{efficiency['q2_activation_rate']:.4f}**. The same operating stress shows up in **{support_product['segment']} / {support_product['channel']} / {support_product['region']}**, where support-product score reaches **{support_product['support_product_score']:.2f}** and ticket rate rises to **{support_product['q2_ticket_rate_per_100_accounts']:.2f}**.

## What to do next

Prioritize the growth budget behind **{growth['segment']} / {growth['channel']}**, contain the deterioration in **{retention['segment']} / {retention['channel']}**, and run a focused cross-functional fix for **{risk['focus_region']}** in **{risk['segment']} / {risk['channel']}** before the next board cycle. The operating question is no longer just how to buy more volume; it is how to protect efficient ARR growth while reducing refund-driven leakage and support drag in the weakest cohorts.
"""


def main() -> None:
    ensure_audit_service()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    metrics = compute_metrics()
    write_csv(OUTPUT_ROOT / "metrics_snapshot.csv", list(metrics[0].keys()), metrics)

    diagnosis, insights = build_diagnosis(metrics)
    (OUTPUT_ROOT / "diagnosis_report.json").write_text(
        json.dumps(diagnosis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = build_summary(insights)
    (OUTPUT_ROOT / "executive_summary.md").write_text(summary, encoding="utf-8")

    manifest = requests.get(f"{API_URL}/manifest", timeout=10).json()
    validation = requests.post(
        f"{API_URL}/validate-metrics",
        json={"metrics": metrics},
        timeout=30,
    )
    validation.raise_for_status()
    validation_payload = validation.json()

    metrics_rows = read_csv_rows(OUTPUT_ROOT / "metrics_snapshot.csv")

    submission = {
        "manifest_id": manifest["manifest_id"],
        "analysis_window": manifest["analysis_window"],
        "metrics_validation_id": validation_payload["validation_id"],
        "metrics_snapshot": metrics_rows,
        "diagnosis_report": diagnosis,
        "executive_summary_markdown": summary,
    }
    (OUTPUT_ROOT / "final_submission.json").write_text(
        json.dumps(submission, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    receipt = requests.post(f"{API_URL}/submit-report", json=submission, timeout=30)
    receipt.raise_for_status()
    (OUTPUT_ROOT / "audit_receipt.json").write_text(
        json.dumps(receipt.json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
