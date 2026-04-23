from __future__ import annotations

import re

from conftest import (
    DIRTY_LEDGER,
    MERCHANTS_PATH,
    OUT_DIR,
    REFERENCE_LEDGER,
    load_csv,
    load_json,
    reference_daily_rows,
    reference_monthly_rows,
    run_gate,
)


def _has_summary_acceptance(summary: str, scenario: str, report_type: str) -> bool:
    patterns = [
        rf"{scenario}.*{report_type}=True",
        rf"{scenario}.*{report_type}: accepted=True",
        rf"{scenario}.*{report_type} accepted: True",
        rf"{scenario}.*{report_type} accepted=True",
    ]
    return any(re.search(pattern, summary, re.DOTALL) for pattern in patterns)


def _normalize_validation_events(events: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for event in events:
        if "scenario" in event and "report_type" in event:
            normalized.append(
                {
                    "path": event["path"],
                    "details": {
                        "scenario": event["scenario"],
                        "report_type": event["report_type"],
                        "accepted": event["accepted"],
                    },
                }
            )
            continue

        details = event.get("details", {})
        report_type = details.get("report_type") if isinstance(details, dict) else None
        if report_type in {"daily", "monthly"}:
            normalized.append(
                {
                    "path": event["path"],
                    "details": {
                        "scenario": details.get("scenario")
                        or event.get("query", {}).get("scenario"),
                        "report_type": report_type,
                        "accepted": details.get("accepted"),
                    },
                }
            )

    return normalized


def _validation_events_from_gate_result(gate_result: dict[str, object]) -> list[dict[str, object]]:
    if "gateway_evidence" in gate_result:
        gateway_evidence = gate_result["gateway_evidence"]  # type: ignore[index]
        if isinstance(gateway_evidence, list):
            return _normalize_validation_events(gateway_evidence)
        if "validated_reports" in gateway_evidence:
            return _normalize_validation_events(gateway_evidence["validated_reports"])  # type: ignore[index]
        if "audit" in gateway_evidence:
            audit = gateway_evidence["audit"]  # type: ignore[index]
            if "complete" in audit:
                assert audit["complete"] is True  # type: ignore[index]
            if "validation_events" in audit:
                return _normalize_validation_events(audit["validation_events"])  # type: ignore[index]
            if "events" in audit:
                return _normalize_validation_events(audit["events"])  # type: ignore[index]
        if "audit_summary" in gateway_evidence:
            audit_summary = gateway_evidence["audit_summary"]  # type: ignore[index]
            if "validation_events" in audit_summary:
                return _normalize_validation_events(audit_summary["validation_events"])  # type: ignore[index]
            if "events" in audit_summary:
                return _normalize_validation_events(audit_summary["events"])  # type: ignore[index]
            if "validation_calls" in audit_summary:
                return _normalize_validation_events(audit_summary["validation_calls"])  # type: ignore[index]
        if "validation_events" in gateway_evidence:
            flattened_events: list[dict[str, object]] = []
            for scenario_event in gateway_evidence["validation_events"]:  # type: ignore[index]
                if "scenario" in scenario_event:
                    if "report_type" in scenario_event:
                        flattened_events.append(
                            {
                                "path": scenario_event["path"],
                                "details": {
                                    "scenario": scenario_event["scenario"],
                                    "report_type": scenario_event["report_type"],
                                    "accepted": scenario_event["accepted"],
                                },
                            }
                        )
                        continue
                    scenario_name = scenario_event["scenario"]
                    for report_type in ("daily", "monthly"):
                        report_event = scenario_event[report_type]
                        flattened_events.append(
                            {
                                "path": report_event["path"],
                                "details": {
                                    "scenario": scenario_name,
                                    "report_type": report_type,
                                    "accepted": report_event["accepted"],
                                },
                            }
                        )
                    continue

                details = scenario_event.get("details", {})
                flattened_events.append(
                    {
                        "path": scenario_event["path"],
                        "details": {
                            "scenario": details.get("scenario")
                            or scenario_event.get("query", {}).get("scenario"),
                            "report_type": details.get("report_type"),
                            "accepted": details.get("accepted"),
                        },
                    }
                )
            return flattened_events
        if "validation_calls" in gateway_evidence:
            return _normalize_validation_events(gateway_evidence["validation_calls"])  # type: ignore[index]

    if "gateway" in gate_result:
        gateway = gate_result["gateway"]  # type: ignore[index]
        if "accepted_validation_events" in gateway:
            return _normalize_validation_events(gateway["accepted_validation_events"])  # type: ignore[index]
        if "validation_audit" in gateway:
            return _normalize_validation_events(gateway["validation_audit"])  # type: ignore[index]
        if "audit_events" in gateway:
            return _normalize_validation_events(gateway["audit_events"])  # type: ignore[index]
        if "validation_events" in gateway:
            return _normalize_validation_events(gateway["validation_events"])  # type: ignore[index]
        if "validation_calls" in gateway:
            return _normalize_validation_events(gateway["validation_calls"])  # type: ignore[index]
        audit = gateway.get("audit", {})
        if "events" in audit:
            return _normalize_validation_events(audit["events"])

    if "gateway_audit" in gate_result:
        return _normalize_validation_events(gate_result["gateway_audit"]["events"])  # type: ignore[index]

    raise AssertionError(f"missing recognizable gateway evidence in gate_result: {gate_result}")


def test_formal_gate_passes_and_outputs_contract() -> None:
    result = run_gate()
    assert result.returncode == 0, result.stderr or result.stdout

    gate_result = load_json(OUT_DIR / "gate_result.json")
    assert gate_result["overall_status"] == "passed"
    assert gate_result["phase_order"] == ["export", "validate", "summarize"]
    assert gate_result["quality_assets"]["all_present"] is True
    assert gate_result["functional_tests"]["passed"] is True
    assert {item["scenario"] for item in gate_result["scenarios"]} == {
        "reference_batch",
        "dirty_incident_batch",
    }


def test_reference_and_dirty_exports_match_behavioral_reference() -> None:
    result = run_gate()
    assert result.returncode == 0, result.stderr or result.stdout

    reference_daily = load_csv(OUT_DIR / "reference_batch_daily.csv")
    reference_monthly = load_csv(OUT_DIR / "reference_batch_monthly.csv")
    dirty_daily = load_csv(OUT_DIR / "dirty_incident_batch_daily.csv")
    dirty_monthly = load_csv(OUT_DIR / "dirty_incident_batch_monthly.csv")

    assert reference_daily == reference_daily_rows(REFERENCE_LEDGER, MERCHANTS_PATH)
    assert reference_monthly == reference_monthly_rows(REFERENCE_LEDGER, MERCHANTS_PATH)
    assert dirty_daily == reference_daily_rows(DIRTY_LEDGER, MERCHANTS_PATH)
    assert dirty_monthly == reference_monthly_rows(DIRTY_LEDGER, MERCHANTS_PATH)


def test_dirty_incident_preserves_adjustments_and_batch_fallbacks() -> None:
    result = run_gate()
    assert result.returncode == 0, result.stderr or result.stdout

    dirty_daily = {
        (row["report_date"], row["merchant_id"]): row
        for row in load_csv(OUT_DIR / "dirty_incident_batch_daily.csv")
    }
    aurora = dirty_daily[("2026-04-16", "m_aurora")]
    beacon = dirty_daily[("2026-04-16", "m_beacon")]

    assert aurora["adjustment_count"] == "3"
    assert aurora["adjustment_amount"] == "-68.00"
    assert aurora["processor_batch_id"] == "stl-20260416-aurora"
    assert beacon["processor_batch_id"] == "stl-20260416-beacon"


def test_export_summary_mentions_gateway_and_quality_assets() -> None:
    result = run_gate()
    assert result.returncode == 0, result.stderr or result.stdout

    summary = (OUT_DIR / "export_summary.md").read_text(encoding="utf-8")
    assert "overall_status: passed" in summary
    assert "gateway_url: http://127.0.0.1:8320" in summary
    assert "quality_assets_present: True" in summary
    assert "functional_tests_passed: True" in summary
    for scenario in ("reference_batch", "dirty_incident_batch"):
        assert scenario in summary
        assert _has_summary_acceptance(summary, scenario, "daily"), summary
        assert _has_summary_acceptance(summary, scenario, "monthly"), summary


def test_real_gateway_endpoints_are_used() -> None:
    result = run_gate()
    assert result.returncode == 0, result.stderr or result.stdout

    gate_result = load_json(OUT_DIR / "gate_result.json")
    expected_pairs = {
        ("reference_batch", "daily"),
        ("reference_batch", "monthly"),
        ("dirty_incident_batch", "daily"),
        ("dirty_incident_batch", "monthly"),
    }
    validation_events = _validation_events_from_gate_result(gate_result)
    seen_pairs = {
        (
            event["details"].get("scenario"),
            event["details"].get("report_type"),
        )
        for event in validation_events
    }
    assert seen_pairs == expected_pairs
    assert len(validation_events) == 4
    for scenario, report_type in expected_pairs:
        expected_path = f"/api/v1/validate/{report_type}"
        assert any(
            event["path"] == expected_path
            and event["details"].get("scenario") == scenario
            and event["details"].get("report_type") == report_type
            and event["details"].get("accepted") is True
            for event in validation_events
        ), validation_events
