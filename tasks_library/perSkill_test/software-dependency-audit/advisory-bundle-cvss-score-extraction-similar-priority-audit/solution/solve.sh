#!/bin/bash
set -euo pipefail

INPUT_JSON="${INPUT_JSON:-/root/advisory_bundle.json}"
OUTPUT_CSV="${OUTPUT_CSV:-/root/advisory_priority_audit.csv}"

python3 - <<'PY'
import csv
import json
import os

input_json = os.environ.get("INPUT_JSON", "/root/advisory_bundle.json")
output_csv = os.environ.get("OUTPUT_CSV", "/root/advisory_priority_audit.csv")


def choose_cvss(entry):
    cvss = entry.get("cvss") or {}
    priority = [
        ("nvd", "NVD"),
        ("ghsa", "GHSA"),
        ("redhat", "RedHat"),
    ]
    for key, label in priority:
        source = cvss.get(key) or {}
        score = source.get("v3_score")
        if score is not None:
            return str(score), label
    return "N/A", "N/A"


rows = []
with open(input_json, "r", encoding="utf-8") as handle:
    bundle = json.load(handle)

for group in bundle.get("advisory_groups", []):
    artifact = group.get("artifact", "")
    for entry in group.get("entries", []):
        severity = entry.get("severity", "")
        if severity not in {"HIGH", "CRITICAL"}:
            continue
        score, source = choose_cvss(entry)
        fixed_version = entry.get("fixed_version") or "N/A"
        rows.append(
            {
                "Artifact": artifact,
                "Package": entry.get("package", ""),
                "Installed_Version": entry.get("installed_version", ""),
                "Advisory_ID": entry.get("advisory_id", ""),
                "Severity": severity,
                "CVSS_Score": score,
                "Score_Source": source,
                "Fixed_Version": fixed_version,
                "Title": entry.get("title", ""),
                "Reference_URL": entry.get("reference_url", ""),
            }
        )

rows.sort(key=lambda item: (item["Artifact"], item["Package"], item["Advisory_ID"]))

fieldnames = [
    "Artifact",
    "Package",
    "Installed_Version",
    "Advisory_ID",
    "Severity",
    "CVSS_Score",
    "Score_Source",
    "Fixed_Version",
    "Title",
    "Reference_URL",
]

with open(output_csv, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
