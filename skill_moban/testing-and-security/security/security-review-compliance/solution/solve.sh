#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "review_findings.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "review_matrix.csv"
output_dir.mkdir(parents=True, exist_ok=True)

components = {}
severity_keys = ("critical", "high", "medium", "low")

with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        component = (row.get("component") or "").strip()
        severity = (row.get("severity") or "").strip().lower()
        data_subject = (row.get("data_subject") or "").strip()
        has_mitigation = (row.get("has_mitigation") or "").strip().lower()

        if component not in components:
            components[component] = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "gdpr_flag": False,
                "mitigation_gap": False,
            }

        if severity in severity_keys:
            components[component][severity] += 1

        if data_subject == "eu_personal_data":
            components[component]["gdpr_flag"] = True

        if has_mitigation == "no":
            components[component]["mitigation_gap"] = True

rows = []
for component in sorted(components):
    item = components[component]
    critical_count = item["critical"]
    high_count = item["high"]
    medium_count = item["medium"]
    low_count = item["low"]
    gdpr_flag = item["gdpr_flag"]
    mitigation_gap = item["mitigation_gap"]

    if critical_count > 0 or high_count >= 2 or (gdpr_flag and mitigation_gap):
        status = "fail"
    elif high_count == 1 or medium_count >= 2:
        status = "warn"
    else:
        status = "pass"

    rows.append(
        {
            "component": component,
            "critical_count": str(critical_count),
            "high_count": str(high_count),
            "medium_count": str(medium_count),
            "low_count": str(low_count),
            "gdpr_flag": "true" if gdpr_flag else "false",
            "status": status,
        }
    )

with output_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = [
        "component",
        "critical_count",
        "high_count",
        "medium_count",
        "low_count",
        "gdpr_flag",
        "status",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
