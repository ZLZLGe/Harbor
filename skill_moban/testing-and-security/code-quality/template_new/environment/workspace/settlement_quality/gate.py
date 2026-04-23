from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from settlement_quality.exporter import build_daily_rows, build_monthly_rows
from settlement_quality.gateway_client import validate_daily, validate_monthly


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

    completed = subprocess.run(
        ["pytest", "-q", str(test_path)],
        cwd=WORKSPACE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "passed": completed.returncode == 0,
        "pytest_exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
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
        "## Scenario Results",
    ]

    for scenario in result["scenarios"]:
        lines.append(
            f"- {scenario['scenario']}: daily={scenario['daily']['accepted']} monthly={scenario['monthly']['accepted']}"
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
    scenario_results = []

    for scenario_name, ledger_path in SCENARIOS.items():
        daily_rows = build_daily_rows(ledger_path, MERCHANTS_PATH)
        monthly_rows = build_monthly_rows(ledger_path, MERCHANTS_PATH)

        write_csv(OUT_DIR / f"{scenario_name}_daily.csv", DAILY_FIELDS, daily_rows)
        write_csv(OUT_DIR / f"{scenario_name}_monthly.csv", MONTHLY_FIELDS, monthly_rows)

        daily_validation = validate_daily(scenario=scenario_name, rows=daily_rows)
        monthly_validation = validate_monthly(scenario=scenario_name, rows=monthly_rows)
        scenario_results.append(
            {
                "scenario": scenario_name,
                "daily": daily_validation,
                "monthly": monthly_validation,
            }
        )

    asset_files = quality_asset_status()
    functional_tests = run_functional_tests()

    all_validations_passed = all(
        item["daily"]["accepted"] and item["monthly"]["accepted"] for item in scenario_results
    )
    all_assets_present = all(asset_files.values())
    overall_passed = all_validations_passed and all_assets_present and functional_tests["passed"]

    result = {
        "overall_status": "passed" if overall_passed else "failed",
        "gateway_url": "http://127.0.0.1:8320",
        "phase_order": ["export", "validate", "summarize"],
        "scenarios": scenario_results,
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
