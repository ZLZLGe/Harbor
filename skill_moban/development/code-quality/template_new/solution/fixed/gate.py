from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from settlement_quality.exporter import build_daily_rows, build_monthly_rows
from settlement_quality.gateway_client import (
    GATEWAY_URL,
    ensure_gateway_running,
    gateway_audit,
    gateway_integrity,
    reset_gateway_audit,
    validate_daily,
    validate_monthly,
)


WORKSPACE_ROOT = Path("/app/workspace")
DATA_ROOT = WORKSPACE_ROOT / "data"
OUT_DIR = WORKSPACE_ROOT / "out"
STATE_DIR = WORKSPACE_ROOT / "state"
QUALITY_DIR = WORKSPACE_ROOT / "quality"
MERCHANTS_PATH = DATA_ROOT / "merchants.json"

SCENARIOS = {
    "reference_batch": DATA_ROOT / "reference" / "ledger.jsonl",
    "dirty_incident_batch": DATA_ROOT / "incidents" / "dirty_incident_ledger.jsonl",
}

REQUIRED_QUALITY_FILES = [
    WORKSPACE_ROOT / "AGENTS.md",
    QUALITY_DIR / "QUALITY.md",
    QUALITY_DIR / "RUN_CODE_REVIEW.md",
    QUALITY_DIR / "RUN_INTEGRATION_TESTS.md",
    QUALITY_DIR / "RUN_SPEC_AUDIT.md",
    QUALITY_DIR / "test_functional.py",
]

DAILY_FIELDS = [
    "report_type",
    "report_date",
    "merchant_id",
    "merchant_name",
    "currency",
    "processor_batch_id",
    "event_count",
    "charge_count",
    "adjustment_count",
    "gross_amount",
    "fee_amount",
    "adjustment_amount",
    "net_settlement_amount",
]

MONTHLY_FIELDS = [
    "report_type",
    "report_month",
    "merchant_id",
    "merchant_name",
    "currency",
    "charge_count",
    "refund_count",
    "chargeback_count",
    "adjustment_count",
    "gross_amount",
    "fee_amount",
    "adjustment_amount",
    "net_settlement_amount",
    "first_settlement_date",
    "last_settlement_date",
    "first_batch_id",
    "last_batch_id",
]


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def quality_asset_status() -> dict[str, bool]:
    return {str(path.relative_to(WORKSPACE_ROOT)): path.exists() for path in REQUIRED_QUALITY_FILES}


def run_functional_tests() -> dict[str, Any]:
    test_path = QUALITY_DIR / "test_functional.py"
    if not test_path.exists():
        return {
            "passed": False,
            "pytest_exit_code": 4,
            "stdout": "",
            "stderr": "missing quality/test_functional.py",
        }

    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{WORKSPACE_ROOT}:{existing_pythonpath}" if existing_pythonpath else str(WORKSPACE_ROOT)
    )
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(test_path)],
        cwd=WORKSPACE_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    return {
        "passed": completed.returncode == 0,
        "pytest_exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def summarize_gateway_evidence(audit_events: list[dict[str, Any]]) -> dict[str, Any]:
    validation_events = [
        event
        for event in audit_events
        if event.get("details", {}).get("report_type") in {"daily", "monthly"}
    ]
    expected_pairs = {
        ("reference_batch", "daily"),
        ("reference_batch", "monthly"),
        ("dirty_incident_batch", "daily"),
        ("dirty_incident_batch", "monthly"),
    }
    seen_pairs = {
        (
            event["details"].get("scenario", ""),
            event["details"].get("report_type", ""),
        )
        for event in validation_events
    }
    return {
        "validation_event_count": len(validation_events),
        "expected_validation_pairs": [
            {"scenario": scenario, "report_type": report_type}
            for scenario, report_type in sorted(expected_pairs)
        ],
        "seen_validation_pairs": [
            {"scenario": scenario, "report_type": report_type}
            for scenario, report_type in sorted(seen_pairs)
        ],
        "complete": len(validation_events) == len(expected_pairs)
        and seen_pairs == expected_pairs
        and all(
            event["details"].get("accepted") is True for event in validation_events
        ),
        "validation_events": validation_events,
    }


def render_summary(result: dict[str, Any]) -> None:
    lines = [
        "# Merchant Settlement Quality Gate",
        "",
        f"- overall_status: {result['overall_status']}",
        f"- gateway_url: {result['gateway_url']}",
        f"- phase_order: {', '.join(result['phase_order'])}",
        f"- quality_assets_present: {result['quality_assets']['all_present']}",
        f"- functional_tests_passed: {result['functional_tests']['passed']}",
        "",
        "## Gateway Evidence",
        f"- server_sha256: {result['gateway_evidence']['integrity']['server_sha256']}",
        f"- data_sha256: {result['gateway_evidence']['integrity']['data_sha256']}",
        f"- validation_event_count: {result['gateway_evidence']['audit']['validation_event_count']}",
        f"- validation_audit_complete: {result['gateway_evidence']['audit']['complete']}",
        "",
        "## Scenario Results",
    ]

    for scenario in result["scenarios"]:
        lines.append(f"### {scenario['scenario']}")
        lines.append(
            f"- daily: accepted={scenario['daily']['accepted']} actual_rows={scenario['daily']['actual_row_count']} expected_rows={scenario['daily']['expected_row_count']}"
        )
        if scenario["daily"]["mismatches"]:
            lines.append(f"- daily_mismatches: {' | '.join(scenario['daily']['mismatches'])}")
        lines.append(
            f"- monthly: accepted={scenario['monthly']['accepted']} actual_rows={scenario['monthly']['actual_row_count']} expected_rows={scenario['monthly']['expected_row_count']}"
        )
        if scenario["monthly"]["mismatches"]:
            lines.append(f"- monthly_mismatches: {' | '.join(scenario['monthly']['mismatches'])}")

    lines.extend(
        [
            "",
            "## Gateway Audit Events",
        ]
    )
    for event in result["gateway_evidence"]["audit"]["validation_events"]:
        details = event["details"]
        lines.append(
            f"- {details['scenario']} {details['report_type']}: accepted={details['accepted']} path={event['path']}"
        )

    lines.extend(
        [
            "",
            "## Quality Assets",
        ]
    )
    for relative_path, present in sorted(result["quality_assets"]["files"].items()):
        lines.append(f"- {relative_path}: {present}")

    (OUT_DIR / "export_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_quality_gate() -> dict[str, Any]:
    ensure_dirs()
    ensure_gateway_running()
    reset_gateway_audit()

    exported_scenarios: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []

    for scenario_name, ledger_path in SCENARIOS.items():
        daily_rows = build_daily_rows(ledger_path, MERCHANTS_PATH)
        monthly_rows = build_monthly_rows(ledger_path, MERCHANTS_PATH)

        daily_path = OUT_DIR / f"{scenario_name}_daily.csv"
        monthly_path = OUT_DIR / f"{scenario_name}_monthly.csv"
        write_csv(daily_path, DAILY_FIELDS, daily_rows)
        write_csv(monthly_path, MONTHLY_FIELDS, monthly_rows)
        exported_scenarios.append(
            {
                "scenario": scenario_name,
                "daily_rows": daily_rows,
                "monthly_rows": monthly_rows,
                "daily_path": str(daily_path),
                "monthly_path": str(monthly_path),
            }
        )

    for exported in exported_scenarios:
        scenario_name = exported["scenario"]
        daily_validation = validate_daily(scenario=scenario_name, rows=exported["daily_rows"])
        monthly_validation = validate_monthly(scenario=scenario_name, rows=exported["monthly_rows"])
        scenario_results.append(
            {
                "scenario": scenario_name,
                "daily": daily_validation,
                "monthly": monthly_validation,
                "artifacts": {
                    "daily_csv": exported["daily_path"],
                    "monthly_csv": exported["monthly_path"],
                },
            }
        )

    asset_files = quality_asset_status()
    integrity = gateway_integrity()
    audit = summarize_gateway_evidence(gateway_audit()["events"])
    functional_tests = run_functional_tests()

    all_validations_passed = all(
        item["daily"]["accepted"] and item["monthly"]["accepted"] for item in scenario_results
    )
    all_assets_present = all(asset_files.values())
    overall_passed = (
        all_validations_passed
        and all_assets_present
        and functional_tests["passed"]
        and audit["complete"]
    )

    result = {
        "overall_status": "passed" if overall_passed else "failed",
        "gateway_url": GATEWAY_URL,
        "phase_order": ["export", "validate", "summarize"],
        "scenarios": scenario_results,
        "gateway_evidence": {
            "integrity": integrity,
            "audit": audit,
        },
        "quality_assets": {
            "all_present": all_assets_present,
            "files": asset_files,
        },
        "functional_tests": functional_tests,
    }

    (OUT_DIR / "gate_result.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    render_summary(result)
    return result


def main() -> None:
    result = run_quality_gate()
    if result["overall_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
