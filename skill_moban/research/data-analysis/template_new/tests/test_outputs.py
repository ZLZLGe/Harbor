from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import requests

from reference_metrics import (
    MONTHS,
    build_metric_index,
    compute_q2_region_rollup,
    compute_reference_metrics,
    read_csv_rows,
    stringify_payload,
    summarize_slice,
)


OUTPUT_ROOT = Path(os.environ.get("BOARD_OUTPUT_ROOT", "/app/output"))
AUDIT_API_URL = os.environ.get("AUDIT_API_URL", "http://127.0.0.1:8321")
METRICS_PATH = OUTPUT_ROOT / "metrics_snapshot.csv"
DIAGNOSIS_PATH = OUTPUT_ROOT / "diagnosis_report.json"
SUMMARY_PATH = OUTPUT_ROOT / "executive_summary.md"
SUBMISSION_PATH = OUTPUT_ROOT / "final_submission.json"
RECEIPT_PATH = OUTPUT_ROOT / "audit_receipt.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_metrics_snapshot() -> list[dict[str, Any]]:
    with METRICS_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def test_a_required_outputs_exist_and_parse() -> None:
    for path in [METRICS_PATH, DIAGNOSIS_PATH, SUMMARY_PATH, SUBMISSION_PATH, RECEIPT_PATH]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path

    diagnosis = load_json(DIAGNOSIS_PATH)
    summary = SUMMARY_PATH.read_text(encoding="utf-8")
    submission = load_json(SUBMISSION_PATH)
    receipt = load_json(RECEIPT_PATH)

    assert isinstance(diagnosis, dict)
    assert summary.strip().startswith("# ")
    assert isinstance(submission, dict)
    assert receipt["accepted"] is True


def test_b_metrics_match_contract_recomputation() -> None:
    expected_rows = sorted(
        compute_reference_metrics(),
        key=lambda row: (row["month"], row["segment"], row["channel"]),
    )
    actual_rows = sorted(
        load_metrics_snapshot(),
        key=lambda row: (row["month"], row["segment"], row["channel"]),
    )
    assert len(actual_rows) == len(expected_rows)
    for actual, expected in zip(actual_rows, expected_rows, strict=True):
        assert actual["month"] == expected["month"]
        assert actual["segment"] == expected["segment"]
        assert actual["channel"] == expected["channel"]
        for field, expected_value in expected.items():
            actual_value = actual[field]
            if expected_value == "":
                assert actual_value == ""
            elif field in {"month", "segment", "channel"}:
                assert actual_value == expected_value
            else:
                assert _as_float(actual_value) == expected_value


def test_c_diagnosis_and_summary_surface_real_business_signals() -> None:
    diagnosis = load_json(DIAGNOSIS_PATH)
    summary = SUMMARY_PATH.read_text(encoding="utf-8")
    metric_index = build_metric_index(compute_reference_metrics())

    assert diagnosis["analysis_window"] == {"start_month": "2025-01", "end_month": "2025-06"}
    assert diagnosis["segments_evaluated"] == ["SMB", "Mid-Market", "Enterprise"]
    assert diagnosis["channels_evaluated"] == ["Organic", "Paid Search", "Paid Social", "Partner"]

    growth = diagnosis["top_growth_drivers"][0]
    for key in [
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
    ]:
        assert key in growth
    growth_slice = summarize_slice(compute_reference_metrics(), growth["segment"], growth["channel"])
    assert growth["q1_net_arr_delta"] == growth_slice["q1_net_arr_delta"]
    assert growth["q2_net_arr_delta"] == growth_slice["q2_net_arr_delta"]
    assert growth["delta_vs_baseline"] == round(
        growth_slice["q2_net_arr_delta"] - growth_slice["q1_net_arr_delta"], 2
    )
    assert growth["q2_revenue_retention_rate"] == growth_slice["q2_revenue_retention_rate"]
    assert growth["q2_activation_rate"] == growth_slice["q2_activation_rate"]
    assert growth["q2_payback_months"] == growth_slice["q2_payback_months"]

    risk = diagnosis["top_risk_drivers"][0]
    for key in [
        "segment",
        "channel",
        "focus_region",
        "risk_score",
        "q2_net_arr_delta",
        "q2_revenue_retention_rate",
        "q2_ticket_rate_per_100_accounts",
        "q2_refund_rate",
        "q2_activation_rate",
        "focus_region_refund_share",
        "break_month",
        "monthly_signal_chain",
        "control_slice",
        "evidence",
    ]:
        assert key in risk
    risk_slice = summarize_slice(compute_reference_metrics(), risk["segment"], risk["channel"])
    assert risk["q2_net_arr_delta"] == risk_slice["q2_net_arr_delta"]
    assert risk["q2_revenue_retention_rate"] == risk_slice["q2_revenue_retention_rate"]
    assert len(risk["monthly_signal_chain"]) == 3
    assert [row["month"] for row in risk["monthly_signal_chain"]] == MONTHS[3:]
    for row in risk["monthly_signal_chain"]:
        metric_row = metric_index[(row["month"], risk["segment"], risk["channel"])]
        assert row["net_arr_delta"] == metric_row["net_arr_delta"]
        assert row["revenue_retention_rate"] == metric_row["revenue_retention_rate"]
        assert row["ticket_rate_per_100_accounts"] == metric_row["ticket_rate_per_100_accounts"]
        assert row["activation_rate"] == metric_row["activation_rate"]
    assert risk["break_month"] in MONTHS[3:]
    assert 0.0 <= risk["focus_region_refund_share"] <= 1.0
    assert risk["control_slice"]["segment"] == risk["segment"]
    assert risk["control_slice"]["channel"] != risk["channel"]
    control_slice = summarize_slice(
        compute_reference_metrics(),
        risk["control_slice"]["segment"],
        risk["control_slice"]["channel"],
    )
    assert risk["control_slice"]["q2_net_arr_delta"] == control_slice["q2_net_arr_delta"]
    assert (
        risk["control_slice"]["q2_revenue_retention_rate"]
        == control_slice["q2_revenue_retention_rate"]
    )
    assert (
        risk["control_slice"]["q2_ticket_rate_per_100_accounts"]
        == control_slice["q2_ticket_rate_per_100_accounts"]
    )
    region_rollup = compute_q2_region_rollup(risk["segment"], risk["channel"])
    focus_region = region_rollup[risk["focus_region"]]
    assert risk["q2_refund_rate"] == focus_region["q2_refund_rate"]
    assert risk["q2_activation_rate"] == focus_region["q2_activation_rate"]
    assert (
        risk["q2_ticket_rate_per_100_accounts"]
        == focus_region["q2_ticket_rate_per_100_accounts"]
    )

    efficiency = diagnosis["efficiency_findings"][0]
    for key in [
        "channel",
        "efficiency_score",
        "q1_cac",
        "q2_cac",
        "q1_payback_months",
        "q2_payback_months",
        "q2_activation_rate",
        "evidence",
    ]:
        assert key in efficiency
        assert efficiency[key] != ""

    retention = diagnosis["retention_findings"][0]
    for key in [
        "segment",
        "channel",
        "retention_deterioration_score",
        "q1_logo_retention_rate",
        "q2_logo_retention_rate",
        "q1_revenue_retention_rate",
        "q2_revenue_retention_rate",
        "evidence",
    ]:
        assert key in retention
    retention_slice = summarize_slice(
        compute_reference_metrics(), retention["segment"], retention["channel"]
    )
    assert retention["q1_logo_retention_rate"] == retention_slice["q1_logo_retention_rate"]
    assert retention["q2_logo_retention_rate"] == retention_slice["q2_logo_retention_rate"]
    assert (
        retention["q1_revenue_retention_rate"]
        == retention_slice["q1_revenue_retention_rate"]
    )
    assert (
        retention["q2_revenue_retention_rate"]
        == retention_slice["q2_revenue_retention_rate"]
    )

    support_product = diagnosis["support_product_findings"][0]
    for key in [
        "segment",
        "channel",
        "region",
        "support_product_score",
        "q2_ticket_rate_per_100_accounts",
        "q2_p1_response_sla_rate",
        "q2_activation_rate",
        "q2_pql_to_paid_rate",
        "evidence",
    ]:
        assert key in support_product
    support_rollup = compute_q2_region_rollup(
        support_product["segment"], support_product["channel"]
    )[support_product["region"]]
    assert (
        support_product["q2_ticket_rate_per_100_accounts"]
        == support_rollup["q2_ticket_rate_per_100_accounts"]
    )
    assert (
        support_product["q2_p1_response_sla_rate"]
        == support_rollup["q2_p1_response_sla_rate"]
    )
    assert support_product["q2_activation_rate"] == support_rollup["q2_activation_rate"]
    assert support_product["q2_pql_to_paid_rate"] == support_rollup["q2_pql_to_paid_rate"]

    assert len(diagnosis["recommended_actions"]) >= 3
    assert growth["segment"] in summary and growth["channel"] in summary
    assert risk["focus_region"] in summary and risk["break_month"] in summary
    assert efficiency["channel"] in summary
    assert support_product["region"] in summary


def test_d_final_submission_matches_saved_outputs_and_live_chain() -> None:
    metrics_rows = load_metrics_snapshot()
    diagnosis = load_json(DIAGNOSIS_PATH)
    submission = load_json(SUBMISSION_PATH)
    receipt = load_json(RECEIPT_PATH)
    summary = SUMMARY_PATH.read_text(encoding="utf-8")

    assert submission["metrics_snapshot"] == metrics_rows
    assert submission["diagnosis_report"] == diagnosis
    assert submission["executive_summary_markdown"] == summary
    assert receipt["accepted"] is True
    assert receipt["request_sha256"]
    assert receipt["request_sha256"] == __import__("hashlib").sha256(
        stringify_payload(submission).encode("utf-8")
    ).hexdigest()


def test_e_current_submission_still_passes_live_audit() -> None:
    submission = load_json(SUBMISSION_PATH)
    validation = requests.post(
        f"{AUDIT_API_URL}/validate-metrics",
        json={"metrics": submission["metrics_snapshot"]},
        timeout=30,
    )
    assert validation.ok, validation.text
    validation_payload = validation.json()
    assert validation_payload["accepted"] is True

    replay = dict(submission)
    replay["metrics_validation_id"] = validation_payload["validation_id"]
    response = requests.post(
        f"{AUDIT_API_URL}/submit-report",
        json=replay,
        timeout=30,
    )
    assert response.ok, response.text
    payload = response.json()
    assert payload["accepted"] is True
