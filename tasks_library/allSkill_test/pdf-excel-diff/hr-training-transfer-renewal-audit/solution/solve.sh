#!/bin/bash
set -euo pipefail

cat > /tmp/solve_training_audit.py <<'PY'
#!/usr/bin/env python3

import json
import re

import pandas as pd
import pdfplumber


PDF_FILE = "/root/archived_training_rosters.pdf"
EXCEL_FILE = "/root/current_training_compliance_tracker.xlsx"
OUTPUT_FILE = "/root/training_compliance_discrepancies.json"
EMPLOYEE_ID_PATTERN = re.compile(r"^EMP\d{4}$")
ARCHIVED_STATUS_MAP = {
    "Complete": ("Current", 3),
    "Grace": ("Grace Period", 2),
    "Expired": ("Expired", 1),
}


def normalize_text(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def normalize_date(value):
    timestamp = pd.to_datetime(value, errors="raise")
    return timestamp.strftime("%Y-%m-%d")


def extract_archived_rows(pdf_path):
    headers = None
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue

                for raw_row in table:
                    cleaned_row = [normalize_text(cell) for cell in raw_row]
                    if not any(cleaned_row):
                        continue

                    if cleaned_row[0] == "Employee ID":
                        headers = cleaned_row
                        continue

                    if headers and EMPLOYEE_ID_PATTERN.match(cleaned_row[0]):
                        rows.append(cleaned_row[: len(headers)])

    if not headers or not rows:
        raise RuntimeError("Unable to extract archived training roster rows from the PDF.")

    dataframe = pd.DataFrame(rows, columns=headers)
    dataframe["archived_status_normalized"] = dataframe["Archived Status"].map(lambda value: ARCHIVED_STATUS_MAP[value][0])
    dataframe["archived_status_rank"] = dataframe["Archived Status"].map(lambda value: ARCHIVED_STATUS_MAP[value][1])
    dataframe["archived_renewal_date"] = dataframe["Renewal Due"].map(normalize_date)
    return dataframe


def load_sheet(sheet_name):
    dataframe = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
    return dataframe.fillna("")


def build_status_guide(status_guide_df):
    return {
        normalize_text(row["Tracker Status"]): (
            normalize_text(row["Normalized Status"]),
            int(row["Severity Rank"]),
        )
        for row in status_guide_df.to_dict("records")
    }


def main():
    archived_df = extract_archived_rows(PDF_FILE)
    compliance_df = load_sheet("Compliance Tracker")
    status_guide_df = load_sheet("Status Guide")
    status_guide = build_status_guide(status_guide_df)

    compliance_df = compliance_df.copy()
    compliance_df["Employee ID"] = compliance_df["Employee ID"].map(normalize_text)
    compliance_df["Employee Name"] = compliance_df["Employee Name"].map(normalize_text)
    compliance_df["Course Code"] = compliance_df["Course Code"].map(normalize_text)
    compliance_df["Tracker Status"] = compliance_df["Tracker Status"].map(normalize_text)
    compliance_df["current_status"] = compliance_df["Tracker Status"].map(lambda value: status_guide[value][0])
    compliance_df["current_rank"] = compliance_df["Tracker Status"].map(lambda value: status_guide[value][1])
    compliance_df["current_renewal_date"] = compliance_df["Renewal Date"].map(normalize_date)

    current_employee_ids = set(compliance_df["Employee ID"])
    current_record_map = {
        (row["Employee ID"], row["Course Code"]): row
        for row in compliance_df.to_dict("records")
    }

    result = {
        "dropped_employees": [],
        "status_regressions": [],
        "renewal_date_mismatches": [],
    }

    dropped_index = {}

    for row in archived_df.to_dict("records"):
        employee_id = row["Employee ID"]
        employee_name = row["Employee Name"]
        course_code = row["Course Code"]

        if employee_id not in current_employee_ids:
            dropped_index[employee_id] = {
                "employee_id": employee_id,
                "employee_name": employee_name,
            }
            continue

        current_row = current_record_map.get((employee_id, course_code))
        if not current_row:
            continue

        if int(current_row["current_rank"]) < int(row["archived_status_rank"]):
            result["status_regressions"].append(
                {
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "course_code": course_code,
                    "archived_status": row["archived_status_normalized"],
                    "current_status": current_row["current_status"],
                }
            )

        if current_row["current_renewal_date"] != row["archived_renewal_date"]:
            result["renewal_date_mismatches"].append(
                {
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "course_code": course_code,
                    "archived_renewal_date": row["archived_renewal_date"],
                    "current_renewal_date": current_row["current_renewal_date"],
                }
            )

    result["dropped_employees"] = sorted(dropped_index.values(), key=lambda item: item["employee_id"])
    result["status_regressions"] = sorted(
        result["status_regressions"],
        key=lambda item: (item["employee_id"], item["course_code"]),
    )
    result["renewal_date_mismatches"] = sorted(
        result["renewal_date_mismatches"],
        key=lambda item: (item["employee_id"], item["course_code"]),
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_training_audit.py
