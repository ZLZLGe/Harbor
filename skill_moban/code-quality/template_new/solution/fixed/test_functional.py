from __future__ import annotations

from pathlib import Path

import pytest

from settlement_quality import gate as gate_module
from settlement_quality.exporter import build_daily_rows, build_monthly_rows
from settlement_quality.gateway_client import (
    ensure_gateway_running,
    gateway_audit,
    reset_gateway_audit,
    validate_daily,
    validate_monthly,
)


WORKSPACE_ROOT = Path("/app/workspace")
MERCHANTS_PATH = WORKSPACE_ROOT / "data" / "merchants.json"
SCENARIOS = {
    "reference_batch": WORKSPACE_ROOT / "data" / "reference" / "ledger.jsonl",
    "dirty_incident_batch": WORKSPACE_ROOT / "data" / "incidents" / "dirty_incident_ledger.jsonl",
}


@pytest.fixture(scope="session", autouse=True)
def gateway_ready() -> None:
    ensure_gateway_running()


def _rows_for(scenario: str, report_type: str) -> list[dict[str, str]]:
    ledger_path = SCENARIOS[scenario]
    if report_type == "daily":
        return build_daily_rows(ledger_path, MERCHANTS_PATH)
    if report_type == "monthly":
        return build_monthly_rows(ledger_path, MERCHANTS_PATH)
    raise AssertionError(f"unexpected report_type: {report_type}")


def _validate(scenario: str, report_type: str, rows: list[dict[str, str]]) -> dict[str, object]:
    if report_type == "daily":
        return validate_daily(scenario=scenario, rows=rows)
    if report_type == "monthly":
        return validate_monthly(scenario=scenario, rows=rows)
    raise AssertionError(f"unexpected report_type: {report_type}")


def _row(rows: list[dict[str, str]], **match: str) -> dict[str, str]:
    for row in rows:
        if all(row[key] == value for key, value in match.items()):
            return row
    raise AssertionError(f"row not found: {match}")


@pytest.mark.parametrize(
    ("scenario", "report_type"),
    [
        ("reference_batch", "daily"),
        ("reference_batch", "monthly"),
        ("dirty_incident_batch", "daily"),
        ("dirty_incident_batch", "monthly"),
    ],
)
def test_export_rows_are_accepted_by_real_gateway(scenario: str, report_type: str) -> None:
    reset_gateway_audit()
    rows = _rows_for(scenario, report_type)

    result = _validate(scenario, report_type, rows)

    assert result["accepted"] is True, result["mismatches"]
    audit_events = gateway_audit()["events"]
    assert any(
        event.get("details", {}).get("scenario") == scenario
        and event.get("details", {}).get("report_type") == report_type
        and event.get("details", {}).get("accepted") is True
        for event in audit_events
    )


def test_dirty_incident_rows_keep_adjustments_and_batch_fallbacks() -> None:
    daily_rows = _rows_for("dirty_incident_batch", "daily")
    monthly_rows = _rows_for("dirty_incident_batch", "monthly")

    aurora = _row(daily_rows, report_date="2026-04-16", merchant_id="m_aurora")
    beacon = _row(daily_rows, report_date="2026-04-16", merchant_id="m_beacon")
    cinder = _row(daily_rows, report_date="2026-04-17", merchant_id="m_cinder")

    assert aurora["adjustment_count"] == "3"
    assert aurora["adjustment_amount"] == "-68.00"
    assert aurora["net_settlement_amount"] == "193.90"
    assert aurora["processor_batch_id"] == "stl-20260416-aurora"
    assert beacon["processor_batch_id"] == "stl-20260416-beacon"
    assert cinder["adjustment_count"] == "1"
    assert cinder["adjustment_amount"] == "-10.00"

    aurora_monthly = _row(monthly_rows, report_month="2026-04", merchant_id="m_aurora")
    assert aurora_monthly["refund_count"] == "1"
    assert aurora_monthly["chargeback_count"] == "1"
    assert aurora_monthly["adjustment_count"] == "3"
    assert aurora_monthly["first_batch_id"] == "stl-20260416-aurora"
    assert aurora_monthly["last_batch_id"] == "stl-20260416-aurora"

    cinder_monthly = _row(monthly_rows, report_month="2026-04", merchant_id="m_cinder")
    assert cinder_monthly["refund_count"] == "1"
    assert cinder_monthly["first_batch_id"] == "stl-20260417-cinder"
    assert cinder_monthly["last_batch_id"] == "stl-20260417-cinder"


def test_gateway_rejects_blank_batch_id_regression() -> None:
    reset_gateway_audit()
    rows = [row.copy() for row in _rows_for("dirty_incident_batch", "daily")]
    beacon = _row(rows, report_date="2026-04-16", merchant_id="m_beacon")
    beacon["processor_batch_id"] = ""

    result = validate_daily(scenario="dirty_incident_batch", rows=rows)

    assert result["accepted"] is False
    assert any("processor_batch_id" in mismatch for mismatch in result["mismatches"])
    assert any(
        event.get("details", {}).get("scenario") == "dirty_incident_batch"
        and event.get("details", {}).get("report_type") == "daily"
        and event.get("details", {}).get("accepted") is False
        for event in gateway_audit()["events"]
    )


def test_gateway_rejects_silent_adjustment_drop_regression() -> None:
    reset_gateway_audit()
    rows = [row.copy() for row in _rows_for("reference_batch", "monthly")]
    aurora_monthly = _row(rows, report_month="2026-04", merchant_id="m_aurora")
    aurora_monthly.update(
        {
            "refund_count": "0",
            "chargeback_count": "0",
            "adjustment_count": "0",
            "adjustment_amount": "0.00",
            "net_settlement_amount": "329.80",
        }
    )

    result = validate_monthly(scenario="reference_batch", rows=rows)

    assert result["accepted"] is False
    assert any("adjustment_amount" in mismatch for mismatch in result["mismatches"])
    assert any(
        event.get("details", {}).get("scenario") == "reference_batch"
        and event.get("details", {}).get("report_type") == "monthly"
        and event.get("details", {}).get("accepted") is False
        for event in gateway_audit()["events"]
    )


def test_gate_main_exits_non_zero_when_quality_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gate_module, "run_quality_gate", lambda: {"overall_status": "failed"})

    with pytest.raises(SystemExit) as exc_info:
        gate_module.main()

    assert exc_info.value.code == 1
