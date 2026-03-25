#!/bin/sh
set -eu

python3 - <<'PY'
import csv
import re
import subprocess

script = "/root/.codex/skills/13f-analyzer/scripts/holding_analysis.py"
with open("/root/2025-q3/COVERPAGE.tsv", newline="") as f:
    cover = list(csv.DictReader(f, delimiter="\t"))
manager_by_accession = {row["ACCESSION_NUMBER"]: row["FILINGMANAGER_NAME"] for row in cover}
rows = []

with open("/root/data/q3_watchlist.csv", newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        stdout = subprocess.check_output(
            ["python3", script, "--cusip", row["cusip"], "--quarter", "2025-q3", "--topk", "1"],
            text=True,
        )
        match = re.search(r"Rank 1: accession number = ([0-9-]+), Holding value = ([0-9.]+)", stdout)
        if not match:
            raise RuntimeError(f"Could not parse holding analysis output:\n{stdout}")
        accession = match.group(1)
        value = float(match.group(2))
        rows.append(
            {
                "cusip": row["cusip"],
                "top_accession": accession,
                "top_manager_name": manager_by_accession[accession],
                "total_value": f"{value:.2f}",
            }
        )

with open("/root/q3_crowding_watchlist.csv", "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=["cusip", "top_accession", "top_manager_name", "total_value"],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
