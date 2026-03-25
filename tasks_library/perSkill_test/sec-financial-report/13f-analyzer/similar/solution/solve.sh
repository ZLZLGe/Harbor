#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import subprocess


script = "/root/.codex/skills/13f-analyzer/scripts/one_fund_analysis.py"
stdout = subprocess.check_output(
    [
        "python3",
        script,
        "--quarter",
        "2025-q3",
        "--accession_number",
        "2000000001-25-000101",
        "--baseline_quarter",
        "2025-q2",
        "--baseline_accession_number",
        "2000000001-25-000001",
    ],
    text=True,
)

aum_match = re.search(r"Summary stats for quarter: 2025-q3.*?Total AUM: ([0-9.]+)", stdout, re.S)
stock_match = re.search(r"Summary stats for quarter: 2025-q3.*?Number of stock holdings: ([0-9]+)", stdout, re.S)
buy_section = stdout.split("Top 10 Buys from 2025-q2 to 2025-q3:", 1)[1].split("Top 10 Sells from 2025-q2 to 2025-q3:", 1)[0]
sell_section = stdout.split("Top 10 Sells from 2025-q2 to 2025-q3:", 1)[1]
buy_cusips = re.findall(r"CUSIP: ([A-Z0-9]+)", buy_section)
sell_cusips = re.findall(r"CUSIP: ([A-Z0-9]+)", sell_section)

if not aum_match or not stock_match or len(buy_cusips) < 3 or len(sell_cusips) < 2:
    raise RuntimeError(f"Could not parse analyzer output:\n{stdout}")

payload = {
    "q3_total_aum": float(aum_match.group(1)),
    "q3_stock_holdings": int(stock_match.group(1)),
    "top_buy_cusips": buy_cusips[:3],
    "top_sell_cusips": sell_cusips[:2],
}

with open("/root/aurora_rotation_summary.json", "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
PY
