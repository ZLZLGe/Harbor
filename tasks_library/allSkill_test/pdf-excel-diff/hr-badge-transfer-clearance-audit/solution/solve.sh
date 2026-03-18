#!/bin/bash
set -euo pipefail

cat > /tmp/solve_badge_audit.py <<'PY'
#!/usr/bin/env python3

import json
import re

import pandas as pd
import pdfplumber


PDF_FILE = "/root/archived_badge_packets.pdf"
EXCEL_FILE = "/root/current_badge_clearance_workbook.xlsx"
OUTPUT_FILE = "/root/badge_clearance_audit.json"
EMPLOYEE_ID_PATTERN = re.compile(r"^EMP\d{4}$")


def normalize_text(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


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
        raise RuntimeError("Unable to extract archived badge packet data from the PDF.")

    return pd.DataFrame(rows, columns=headers)


def load_sheet(excel_path, sheet_name):
    dataframe = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str)
    return dataframe.fillna("").applymap(normalize_text)


def compare_records(archived_df, badge_roster_df, zone_assignments_df, clearance_registry_df, policy_df):
    badge_roster_by_badge = badge_roster_df.set_index("Badge ID").to_dict("index")
    zone_by_badge = zone_assignments_df.set_index("Badge ID")["Access Zone"].to_dict()
    clearance_by_employee = clearance_registry_df.set_index("Employee ID")["Clearance Level"].to_dict()
    policy_by_zone = policy_df.set_index("Access Zone")["Required Clearance"].to_dict()

    result = {
        "removed_badges": [],
        "zone_changes": [],
        "clearance_policy_violations": [],
    }

    for row in archived_df.to_dict("records"):
        employee_id = row["Employee ID"]
        badge_id = row["Badge ID"]
        archived_zone = row["Access Zone"]

        current_badge_record = badge_roster_by_badge.get(badge_id)
        if (
            not current_badge_record
            or current_badge_record.get("Employee ID") != employee_id
            or current_badge_record.get("Badge Status") != "Active"
        ):
            result["removed_badges"].append(
                {
                    "employee_id": employee_id,
                    "badge_id": badge_id,
                }
            )
            continue

        current_zone = zone_by_badge.get(badge_id)
        if not current_zone:
            raise RuntimeError(f"Missing current zone for badge {badge_id}")

        if archived_zone != current_zone:
            result["zone_changes"].append(
                {
                    "employee_id": employee_id,
                    "badge_id": badge_id,
                    "old_zone": archived_zone,
                    "new_zone": current_zone,
                }
            )

        actual_clearance = clearance_by_employee.get(employee_id)
        if not actual_clearance:
            raise RuntimeError(f"Missing current clearance for employee {employee_id}")

        required_clearance = policy_by_zone.get(current_zone)
        if not required_clearance:
            raise RuntimeError(f"Missing policy row for zone {current_zone}")

        if actual_clearance != required_clearance:
            result["clearance_policy_violations"].append(
                {
                    "employee_id": employee_id,
                    "badge_id": badge_id,
                    "zone": current_zone,
                    "required_clearance": required_clearance,
                    "actual_clearance": actual_clearance,
                }
            )

    for key in result:
        result[key] = sorted(result[key], key=lambda item: item["employee_id"])

    return result


def main():
    archived_df = extract_archived_rows(PDF_FILE)
    badge_roster_df = load_sheet(EXCEL_FILE, "Badge Roster")
    zone_assignments_df = load_sheet(EXCEL_FILE, "Zone Assignments")
    clearance_registry_df = load_sheet(EXCEL_FILE, "Clearance Registry")
    policy_df = load_sheet(EXCEL_FILE, "Policy Matrix")

    result = compare_records(
        archived_df,
        badge_roster_df,
        zone_assignments_df,
        clearance_registry_df,
        policy_df,
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_badge_audit.py
