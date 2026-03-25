#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import re
import subprocess


script = "/root/.codex/skills/13f-analyzer/scripts/one_fund_analysis.py"
rows = []

with open("/root/data/fund_pairs.csv", newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        stdout = subprocess.check_output(
            [
                "python3",
                script,
                "--quarter",
                "2025-q3",
                "--accession_number",
                row["q3_accession"],
                "--baseline_quarter",
                "2025-q2",
                "--baseline_accession_number",
                row["q2_accession"],
            ],
            text=True,
        )
        aum_match = re.search(r"Summary stats for quarter: 2025-q3.*?Total AUM: ([0-9.]+)", stdout, re.S)
        buy_section = stdout.split("Top 10 Buys from 2025-q2 to 2025-q3:", 1)[1].split("Top 10 Sells from 2025-q2 to 2025-q3:", 1)[0]
        sell_section = stdout.split("Top 10 Sells from 2025-q2 to 2025-q3:", 1)[1]
        buy_cusips = re.findall(r"CUSIP: ([A-Z0-9]+)", buy_section)
        sell_cusips = re.findall(r"CUSIP: ([A-Z0-9]+)", sell_section)
        if not aum_match or not buy_cusips or not sell_cusips:
            raise RuntimeError(f"Could not parse analyzer output:\n{stdout}")
        rows.append(
            {
                "fund_label": row["fund_label"],
                "q3_accession": row["q3_accession"],
                "q3_total_aum": f"{float(aum_match.group(1)):.1f}",
                "largest_buy_cusip": buy_cusips[0],
                "largest_sell_cusip": sell_cusips[0],
            }
        )

with open("/root/rotation_digest.csv", "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=["fund_label", "q3_accession", "q3_total_aum", "largest_buy_cusip", "largest_sell_cusip"],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
