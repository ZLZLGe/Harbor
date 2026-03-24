#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from datetime import datetime
import re

import pandas as pd
import pdfplumber

INPUT_FILE = "/root/maintenance_notice_packet"
OUTPUT_FILE = "/root/maintenance_downtime_schedule.csv"

ROW_PATTERN = re.compile(
    r"^(LINE-\d{2})\s+"
    r"(\d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2})\s+"
    r"(\d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2})\s+"
    r"(\d+(?:\.\d)?)\s+"
)

records = []
with pdfplumber.open(INPUT_FILE) as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            match = ROW_PATTERN.match(line.strip())
            if not match:
                continue

            production_line, start_raw, end_raw, hours_raw = match.groups()
            start_dt = datetime.strptime(start_raw, "%d %b %Y %H:%M")
            end_dt = datetime.strptime(end_raw, "%d %b %Y %H:%M")

            records.append(
                {
                    "production_line": production_line,
                    "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                    "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
                    "planned_downtime_hours": float(hours_raw),
                }
            )

df = pd.DataFrame(records)
df = df.sort_values(["start_time", "production_line"], kind="stable").reset_index(drop=True)
df.to_csv(OUTPUT_FILE, index=False)
PY
