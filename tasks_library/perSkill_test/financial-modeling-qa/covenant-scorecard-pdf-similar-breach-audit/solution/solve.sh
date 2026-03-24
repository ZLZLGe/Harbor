#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

PDF_PATH = Path("/root/covenant_package.pdf")
XLSX_PATH = Path("/root/quarterly_financials.xlsx")
OUT_PATH = Path("/root/covenant_breach_summary.json")


def extract_pdf_lines(path: Path) -> list[str]:
    data = path.read_bytes()
    chunks = re.findall(rb"\((.*?)\)\s*Tj", data, flags=re.S)
    lines = []
    for chunk in chunks:
        text = chunk.decode("latin-1")
        text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
        lines.append(text)
    return lines


def load_quarterly_rows(path: Path) -> list[dict[str, object]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as zf:
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))

    raw_rows = []
    for row in root.find("main:sheetData", ns):
        values = []
        for cell in row.findall("main:c", ns):
            if cell.attrib.get("t") == "inlineStr":
                value = cell.findtext("main:is/main:t", default="", namespaces=ns)
            else:
                value = cell.findtext("main:v", default="", namespaces=ns)
            values.append(value)
        raw_rows.append(values)

    header = raw_rows[0]
    numeric_fields = {
        "Base EBITDA",
        "Permitted EBITDA Addback",
        "Maintenance Capex",
        "Cash Taxes",
        "Cash Interest",
        "Interest Income",
        "Scheduled Amortization",
        "Total Debt",
        "Senior Secured Debt",
        "Unrestricted Cash",
        "Cash Netting Cap",
    }

    records = []
    for raw in raw_rows[1:]:
        record = {}
        for key, value in zip(header, raw):
            if key in numeric_fields:
                record[key] = float(value)
            else:
                record[key] = value
        records.append(record)
    return records


def parse_schedule(lines: list[str]) -> list[tuple[str, str | None, str | None, dict[str, float]]]:
    schedule = []
    pattern = re.compile(
        r"Total Net Leverage Ratio max ([0-9.]+) \| "
        r"Senior Secured Leverage Ratio max ([0-9.]+) \| "
        r"Fixed Charge Coverage Ratio min ([0-9.]+)"
    )

    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        limits = {
            "Total Net Leverage Ratio": float(match.group(1)),
            "Senior Secured Leverage Ratio": float(match.group(2)),
            "Fixed Charge Coverage Ratio": float(match.group(3)),
        }
        if line.startswith("Testing date <="):
            end = re.search(r"<= ([0-9-]+)", line).group(1)
            schedule.append(("lte", None, end, limits))
        elif "through" in line:
            start, end = re.search(r"([0-9-]+) through ([0-9-]+)", line).groups()
            schedule.append(("range", start, end, limits))
        elif line.startswith("Testing date >="):
            start = re.search(r">= ([0-9-]+)", line).group(1)
            schedule.append(("gte", start, None, limits))
    return schedule


def threshold_for_date(test_date: str, schedule: list[tuple[str, str | None, str | None, dict[str, float]]]) -> dict[str, float]:
    for mode, start, end, limits in schedule:
        if mode == "lte" and test_date <= end:
            return limits
        if mode == "range" and start <= test_date <= end:
            return limits
        if mode == "gte" and test_date >= start:
            return limits
    raise ValueError(f"No covenant schedule found for {test_date}")


def rounded(value: float) -> float:
    return round(value + 1e-12, 3)


pdf_lines = extract_pdf_lines(PDF_PATH)
pdf_text = "\n".join(pdf_lines)

metric_order_line = next(line for line in pdf_lines if "|" in line and "Leverage Ratio" in line and "Coverage Ratio" in line)
metric_order = [part.strip() for part in metric_order_line.split("|")]

addback_cap_pct = float(re.search(r"([0-9]+)% of Trailing Base EBITDA", pdf_text).group(1)) / 100.0
q4_cash_increment = float(re.search(r"increase Cash Netting Cap by ([0-9.]+)", pdf_text).group(1))
waiver_match = re.search(
    r"do not test ([A-Za-z ]+?) or ([A-Za-z ]+?)\n\s*for that date",
    pdf_text,
)
waived_metrics = {waiver_match.group(1).strip(), waiver_match.group(2).strip()}
schedule = parse_schedule(pdf_lines)

rows = load_quarterly_rows(XLSX_PATH)
breach_periods = []
most_severe = None

for idx, row in enumerate(rows):
    if row["Testing Eligible"] != "Yes":
        continue

    window = rows[idx - 3 : idx + 1]
    trailing_base = sum(item["Base EBITDA"] for item in window)
    trailing_addback = sum(item["Permitted EBITDA Addback"] for item in window)
    ltm_ebitda = trailing_base + min(trailing_addback, addback_cap_pct * trailing_base)

    ltm_capex = sum(item["Maintenance Capex"] for item in window)
    ltm_taxes = sum(item["Cash Taxes"] for item in window)
    ltm_interest = sum(item["Cash Interest"] for item in window)
    ltm_interest_income = sum(item["Interest Income"] for item in window)
    ltm_amortization = sum(item["Scheduled Amortization"] for item in window)

    test_date = row["Quarter End"]
    cash_cap = row["Cash Netting Cap"] + (q4_cash_increment if test_date.endswith("-12-31") else 0.0)
    allowed_cash_netting = min(row["Unrestricted Cash"], cash_cap)

    actuals = {
        "Total Net Leverage Ratio": (row["Total Debt"] - allowed_cash_netting) / ltm_ebitda,
        "Senior Secured Leverage Ratio": (row["Senior Secured Debt"] - allowed_cash_netting) / ltm_ebitda,
        "Fixed Charge Coverage Ratio": (
            ltm_ebitda - ltm_capex - ltm_taxes
        ) / (ltm_interest - ltm_interest_income + ltm_amortization),
    }
    thresholds = threshold_for_date(test_date, schedule)

    breaches = []
    for metric in metric_order:
        if row["Holiday Waiver"] == "Yes" and metric in waived_metrics:
            continue

        actual = actuals[metric]
        threshold = thresholds[metric]
        if metric == "Fixed Charge Coverage Ratio":
            breached = actual < threshold
            deviation = threshold - actual
            direction = "below_minimum"
        else:
            breached = actual > threshold
            deviation = actual - threshold
            direction = "above_maximum"

        if not breached:
            continue

        breach = {
            "metric": metric,
            "actual": rounded(actual),
            "threshold": rounded(threshold),
            "breach_direction": direction,
            "deviation": rounded(deviation),
        }
        breaches.append(breach)

        candidate = {"test_period": test_date, **breach}
        if most_severe is None or candidate["deviation"] > most_severe["deviation"]:
            most_severe = candidate

    if breaches:
        breach_periods.append({"test_period": test_date, "breaches": breaches})

result = {
    "breach_periods": breach_periods,
    "most_severe_breach": most_severe,
}

with OUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
