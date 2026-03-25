#!/bin/sh
set -eu

python3 - <<'PY'
import csv
import re
import subprocess

script = "/root/.codex/skills/13f-analyzer/scripts/one_fund_analysis.py"
with open("/root/2025-q3/COVERPAGE.tsv", newline="") as f:
    cover = list(csv.DictReader(f, delimiter="\t"))
manager_by_accession = {row["ACCESSION_NUMBER"]: row["FILINGMANAGER_NAME"] for row in cover}
rows = []

for accession in [line.strip() for line in open("/root/data/q3_accessions.txt", encoding="utf-8") if line.strip()]:
    stdout = subprocess.check_output(
        ["python3", script, "--quarter", "2025-q3", "--accession_number", accession],
        text=True,
    )
    aum_match = re.search(r"Total AUM: ([0-9.]+)", stdout)
    stock_match = re.search(r"Number of stock holdings: ([0-9]+)", stdout)
    if not aum_match or not stock_match:
        raise RuntimeError(f"Could not parse one-fund summary output:\n{stdout}")
    rows.append(
        {
            "accession": accession,
            "manager_name": manager_by_accession[accession],
            "total_aum": float(aum_match.group(1)),
            "stock_holdings": int(stock_match.group(1)),
        }
    )

rows.sort(key=lambda row: (-row["total_aum"], row["accession"]))

with open("/root/q3_manager_league.tsv", "w", encoding="utf-8") as fh:
    fh.write("accession\tmanager_name\ttotal_aum\tstock_holdings\n")
    for row in rows:
        fh.write(
            f"{row['accession']}\t{row['manager_name']}\t{row['total_aum']:.1f}\t{row['stock_holdings']}\n"
        )
PY
