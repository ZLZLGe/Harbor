#!/bin/bash
set -e

python3 <<'PY'
import csv
import json
import os

ASSET_CSV = os.environ.get("ASSET_CSV_PATH", "/root/asset_exposure.csv")
VULN_JSON = os.environ.get("VULN_JSON_PATH", "/root/vulnerability_records.json")
OUTPUT_TSV = os.environ.get("REMEDIATION_QUEUE_PATH", "/root/remediation_queue.tsv")


def select_score(cvss):
    for key, label in (("nvd", "NVD"), ("ghsa", "GHSA"), ("redhat", "RedHat")):
        source = cvss.get(key)
        if source and source.get("v3_score") is not None:
            return float(source["v3_score"]), label
    return None, "N/A"


def exposure_points(asset):
    hosts = int(asset["exposed_hosts"])
    if hosts >= 200:
        host_points = 3
    elif hosts >= 50:
        host_points = 2
    else:
        host_points = 1
    internet_points = 2 if asset["internet_exposed"] == "yes" else 0
    return int(asset["criticality"]) + internet_points + host_points


def remediation_band(priority_score):
    if priority_score >= 60.0:
        return "P1"
    if priority_score >= 35.0:
        return "P2"
    return "P3"


with open(ASSET_CSV, "r", encoding="utf-8", newline="") as handle:
    asset_rows = list(csv.DictReader(handle))

assets = {row["asset_id"]: row for row in asset_rows}

with open(VULN_JSON, "r", encoding="utf-8") as handle:
    records = json.load(handle)["records"]

queue_rows = []
for record in records:
    asset = assets[record["asset_id"]]
    selected_score, score_source = select_score(record.get("cvss", {}))
    asset_points = exposure_points(asset)
    priority_score = 0.0 if selected_score is None else round(selected_score * asset_points, 1)
    queue_rows.append(
        {
            "Asset_ID": asset["asset_id"],
            "Business_Service": asset["business_service"],
            "Environment": asset["environment"],
            "Vulnerability_ID": record["vulnerability_id"],
            "Package": record["package"],
            "Installed_Version": record["installed_version"],
            "Selected_CVSS": "N/A" if selected_score is None else f"{selected_score:.1f}",
            "Score_Source": score_source,
            "Exposure_Points": str(asset_points),
            "Priority_Score": f"{priority_score:.1f}",
            "Remediation_Band": remediation_band(priority_score),
            "Patch_Window": asset["patch_window"],
            "Fixed_Version": record.get("fixed_version") or "N/A",
            "Reference_URL": record["reference_url"],
        }
    )

queue_rows.sort(
    key=lambda item: (
        -float(item["Priority_Score"]),
        item["Asset_ID"],
        item["Vulnerability_ID"],
    )
)

headers = [
    "Queue_Position",
    "Asset_ID",
    "Business_Service",
    "Environment",
    "Vulnerability_ID",
    "Package",
    "Installed_Version",
    "Selected_CVSS",
    "Score_Source",
    "Exposure_Points",
    "Priority_Score",
    "Remediation_Band",
    "Patch_Window",
    "Fixed_Version",
    "Reference_URL",
]

with open(OUTPUT_TSV, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=headers, delimiter="\t")
    writer.writeheader()
    for index, row in enumerate(queue_rows, start=1):
        row["Queue_Position"] = str(index)
        writer.writerow(row)
PY
