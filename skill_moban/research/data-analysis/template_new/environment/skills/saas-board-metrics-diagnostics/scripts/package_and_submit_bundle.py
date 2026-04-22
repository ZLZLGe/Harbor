#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import requests


OUTPUT_ROOT = Path(os.environ.get("BOARD_OUTPUT_ROOT", "/app/output"))
API_URL = os.environ.get("AUDIT_API_URL", "http://127.0.0.1:8321")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    metrics_path = OUTPUT_ROOT / "metrics_snapshot.csv"
    diagnosis_path = OUTPUT_ROOT / "diagnosis_report.json"
    summary_path = OUTPUT_ROOT / "executive_summary.md"

    metrics = read_csv_rows(metrics_path)
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    summary = summary_path.read_text(encoding="utf-8")

    manifest = requests.get(f"{API_URL}/manifest", timeout=10).json()
    validation = requests.post(
        f"{API_URL}/validate-metrics",
        json={"metrics": metrics},
        timeout=30,
    )
    validation.raise_for_status()
    validation_payload = validation.json()

    final_submission = {
        "manifest_id": manifest["manifest_id"],
        "analysis_window": manifest["analysis_window"],
        "metrics_validation_id": validation_payload["validation_id"],
        "metrics_snapshot": metrics,
        "diagnosis_report": diagnosis,
        "executive_summary_markdown": summary,
    }
    (OUTPUT_ROOT / "final_submission.json").write_text(
        json.dumps(final_submission, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    receipt = requests.post(
        f"{API_URL}/submit-report",
        json=final_submission,
        timeout=30,
    )
    receipt.raise_for_status()
    (OUTPUT_ROOT / "audit_receipt.json").write_text(
        json.dumps(receipt.json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(receipt.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
