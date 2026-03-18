#!/bin/bash
set -euo pipefail

cat > /tmp/solve_benefits_diff.py <<'PY'
#!/usr/bin/env python3

import json
import re

import pandas as pd
import pdfplumber


PDF_FILE = "/root/archived_benefits_snapshot.pdf"
EXCEL_FILE = "/root/current_benefits_enrollment.xlsx"
OUTPUT_FILE = "/root/benefits_enrollment_diff.json"
ID_PATTERN = re.compile(r"^BEN\d{4}$")


def normalize_cell(cell):
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def extract_archived_snapshot(pdf_path):
    headers = None
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue

                for raw_row in table:
                    cleaned_row = [normalize_cell(cell) for cell in raw_row]
                    if not any(cleaned_row):
                        continue

                    if cleaned_row[0] == "Employee ID":
                        headers = cleaned_row
                        continue

                    if headers and ID_PATTERN.match(cleaned_row[0]):
                        rows.append(cleaned_row[: len(headers)])

    if not headers or not rows:
        raise RuntimeError("Unable to extract archived benefits table from PDF.")

    df = pd.DataFrame(rows, columns=headers)
    df["Dependent Count"] = pd.to_numeric(df["Dependent Count"], errors="raise").astype(int)
    return df


def load_current_enrollment(excel_path):
    df = pd.read_excel(excel_path)
    df["Dependent Count"] = pd.to_numeric(df["Dependent Count"], errors="raise").astype(int)
    return df


def compare_snapshots(archived_df, current_df):
    archived_indexed = archived_df.set_index("Employee ID")
    current_indexed = current_df.set_index("Employee ID")

    archived_ids = set(archived_indexed.index)
    current_ids = set(current_indexed.index)

    result = {
        "removed_employees": sorted(archived_ids - current_ids),
        "tier_changes": [],
        "dependent_count_changes": [],
        "salary_band_changes": [],
    }

    for employee_id in sorted(archived_ids & current_ids):
        old_row = archived_indexed.loc[employee_id]
        new_row = current_indexed.loc[employee_id]

        old_tier = str(old_row["Plan Tier"])
        new_tier = str(new_row["Plan Tier"])
        if old_tier != new_tier:
            result["tier_changes"].append(
                {
                    "employee_id": employee_id,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                }
            )

        old_dependents = int(old_row["Dependent Count"])
        new_dependents = int(new_row["Dependent Count"])
        if old_dependents != new_dependents:
            result["dependent_count_changes"].append(
                {
                    "employee_id": employee_id,
                    "old_dependents": old_dependents,
                    "new_dependents": new_dependents,
                }
            )

        old_salary_band = str(old_row["Salary Band"])
        new_salary_band = str(new_row["Salary Band"])
        if old_salary_band != new_salary_band:
            result["salary_band_changes"].append(
                {
                    "employee_id": employee_id,
                    "old_salary_band": old_salary_band,
                    "new_salary_band": new_salary_band,
                }
            )

    return result


def main():
    archived_df = extract_archived_snapshot(PDF_FILE)
    current_df = load_current_enrollment(EXCEL_FILE)
    result = compare_snapshots(archived_df, current_df)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_benefits_diff.py
