#!/bin/bash
set -euo pipefail

cat > /tmp/lab_qc_solve.py <<'PY'
import json
import statistics
from collections import Counter, defaultdict

from openpyxl import load_workbook

INPUT_FILE = "/root/lab_qc_runbook.xlsx"
OUTPUT_FILE = "/root/lab_qc_exceptions.json"


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def load_table(workbook, sheet_name, required_columns):
    ws = workbook[sheet_name]
    header_row = None
    header_map = None

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        normalized = [clean_text(cell) for cell in row]
        if all(column in normalized for column in required_columns):
            header_row = row_idx
            header_map = {column: normalized.index(column) for column in required_columns}
            break

    if header_row is None or header_map is None:
        raise ValueError(f"Could not find header row in {sheet_name}")

    records = []
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        values = []
        for column in required_columns:
            idx = header_map[column]
            values.append(row[idx] if idx < len(row) else None)
        if all(value is None or clean_text(value) == "" for value in values):
            continue
        records.append(dict(zip(required_columns, values)))
    return records


def as_float(value):
    return float(value)


def main():
    workbook = load_workbook(INPUT_FILE, data_only=True)

    batch_rows = load_table(
        workbook,
        "Batch Summary",
        ["batch_id", "panel", "duplicate_variance_limit"],
    )
    plate_rows = load_table(
        workbook,
        "Plate Map",
        ["batch_id", "well", "entry_type", "sample_id", "control_code", "duplicate_group"],
    )
    reading_rows = load_table(workbook, "Readings", ["batch_id", "well", "signal"])
    limit_rows = load_table(workbook, "QC Limits", ["control_code", "min_signal", "max_signal"])
    intake_rows = load_table(workbook, "Specimen Intake", ["intake_id", "sample_id", "patient_id"])

    reading_lookup = {
        (clean_text(row["batch_id"]), clean_text(row["well"])): as_float(row["signal"])
        for row in reading_rows
    }
    limit_lookup = {
        clean_text(row["control_code"]): (
            as_float(row["min_signal"]),
            as_float(row["max_signal"]),
        )
        for row in limit_rows
    }
    variance_limit_lookup = {
        clean_text(row["batch_id"]): as_float(row["duplicate_variance_limit"])
        for row in batch_rows
    }

    failed_control_wells = []
    duplicate_groups = defaultdict(list)

    for row in plate_rows:
        batch_id = clean_text(row["batch_id"])
        well = clean_text(row["well"])
        entry_type = clean_text(row["entry_type"])

        if entry_type == "CONTROL":
            control_code = clean_text(row["control_code"])
            signal = reading_lookup[(batch_id, well)]
            min_signal, max_signal = limit_lookup[control_code]
            if not (min_signal <= signal <= max_signal):
                failed_control_wells.append(
                    {
                        "batch_id": batch_id,
                        "well": well,
                        "control_code": control_code,
                        "signal": signal,
                    }
                )

        if entry_type == "DUPLICATE":
            group_name = clean_text(row["duplicate_group"])
            if group_name:
                duplicate_groups[(batch_id, group_name)].append(
                    {
                        "well": well,
                        "sample_id": clean_text(row["sample_id"]),
                    }
                )

    failed_control_wells.sort(key=lambda item: (item["batch_id"], item["well"]))

    intake_counts = Counter()
    for row in intake_rows:
        sample_id = clean_text(row["sample_id"])
        if sample_id:
            intake_counts[sample_id] += 1
    duplicate_sample_ids = sorted(
        sample_id for sample_id, count in intake_counts.items() if count > 1
    )

    high_variance_batches = []
    for (batch_id, group_name), members in duplicate_groups.items():
        signals = [reading_lookup[(batch_id, member["well"])] for member in members]
        variance = round(statistics.pvariance(signals), 2)
        limit_value = variance_limit_lookup[batch_id]
        if variance > limit_value:
            high_variance_batches.append(
                {
                    "batch_id": batch_id,
                    "duplicate_group": group_name,
                    "sample_id": members[0]["sample_id"],
                    "variance": variance,
                    "variance_limit": limit_value,
                }
            )

    high_variance_batches.sort(key=lambda item: (item["batch_id"], item["duplicate_group"]))

    output = {
        "failed_control_wells": failed_control_wells,
        "duplicate_sample_ids": duplicate_sample_ids,
        "high_variance_batches": high_variance_batches,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /tmp/lab_qc_solve.py
