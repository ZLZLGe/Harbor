#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import io
import json
from pathlib import Path


def choose_cvss(record):
    cvss = record.get("cvss", {})
    for source in ("nvd", "ghsa", "redhat"):
        score = cvss.get(source, {}).get("V3Score")
        if score is not None:
            return score, source, "v3"
    v2 = cvss.get("nvd", {}).get("V2Score")
    if v2 is not None:
        return v2, "nvd", "v2"
    return "N/A", "none", "none"


def format_score(score):
    if isinstance(score, (int, float)):
        return f"{score:.1f}"
    return score


config = json.loads(Path("/root/data/task_config.json").read_text())
records = json.loads(Path(config["input_file"]).read_text())
output_path = Path(config["output_file"])
output_path.parent.mkdir(parents=True, exist_ok=True)
mode = config["mode"]

if mode == "select_scores":
    rows = []
    for record in records:
        score, source, version = choose_cvss(record)
        rows.append(
            {
                "package": record["package"],
                "cve_id": record["cve_id"],
                "selected_score": score,
                "selected_source": source,
                "selected_version": version,
            }
        )
    output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
elif mode == "gate_decisions":
    headers = ["Package", "CVE_ID", "Selected_Score", "Selected_Source", "Release_Gate"]
    rows = []
    for record in records:
        score, source, _version = choose_cvss(record)
        if score == "N/A":
            gate = "manual-review"
        elif score >= 9.0:
            gate = "block"
        elif score >= 7.0:
            gate = "review"
        else:
            gate = "monitor"
        rows.append(
            {
                "Package": record["package"],
                "CVE_ID": record["cve_id"],
                "Selected_Score": format_score(score),
                "Selected_Source": source,
                "Release_Gate": gate,
            }
        )
    priority = {"block": 0, "review": 1, "manual-review": 2, "monitor": 3}
    rows.sort(key=lambda row: (priority[row["Release_Gate"]], row["Package"], row["CVE_ID"]))
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
elif mode == "provenance_brief":
    lines = ["# CVSS Provenance Brief", ""]
    for record in records:
        score, source, version = choose_cvss(record)
        if source == "nvd" and version == "v3":
            continue
        lines.append(f"- {record['cve_id']} ({record['package']}): {format_score(score)} via {source} {version}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
elif mode == "package_matrix":
    package_rows = {}
    for record in records:
        score, source, _version = choose_cvss(record)
        score_value = -1.0 if score == "N/A" else float(score)
        item = package_rows.setdefault(
            record["package"],
            {"Package": record["package"], "Max_Score": score, "Selected_Source": source, "Blocking_CVEs": 0},
        )
        current = -1.0 if item["Max_Score"] == "N/A" else float(item["Max_Score"])
        if score_value > current:
            item["Max_Score"] = score
            item["Selected_Source"] = source
        if score != "N/A" and float(score) >= 8.5:
            item["Blocking_CVEs"] += 1
    rows = sorted(package_rows.values(), key=lambda row: (-1.0 if row["Max_Score"] == "N/A" else -float(row["Max_Score"]), row["Package"]))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["Package", "Max_Score", "Selected_Source", "Blocking_CVEs"], delimiter="\t")
    writer.writeheader()
    for row in rows:
        row = dict(row)
        row["Max_Score"] = format_score(row["Max_Score"])
        writer.writerow(row)
    output_path.write_text(buffer.getvalue(), encoding="utf-8")
else:
    raise RuntimeError(f"Unsupported mode: {mode}")
PY
