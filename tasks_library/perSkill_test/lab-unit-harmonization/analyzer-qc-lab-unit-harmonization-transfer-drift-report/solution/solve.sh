#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import math
import pandas as pd

INPUT_LOG = "/root/environment/data/qc_measurement_log.csv"
REFERENCE = "/root/environment/data/qc_target_ranges.csv"
OUTPUT = "/root/analyzer_qc_drift_report.csv"


def parse_value(raw):
    if pd.isna(raw):
        return None
    text = str(raw).strip()
    if text == "":
        return None
    if "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def convert_value(test_code, value, source_unit, target_unit):
    if source_unit == target_unit:
        return value
    if test_code == "CREA" and source_unit == "umol/L" and target_unit == "mg/dL":
        return value / 88.4
    if test_code == "GLU" and source_unit == "mmol/L" and target_unit == "mg/dL":
        return value / 0.0555
    if test_code == "HGB" and source_unit == "g/L" and target_unit == "g/dL":
        return value / 10.0
    if test_code == "HGB" and source_unit == "mmol/L" and target_unit == "g/dL":
        return value / 0.6206
    if test_code == "CA" and source_unit == "mmol/L" and target_unit == "mg/dL":
        return value / 0.25
    if test_code == "CA" and source_unit == "mEq/L" and target_unit == "mg/dL":
        return value / 0.5
    if test_code == "PHOS" and source_unit == "mmol/L" and target_unit == "mg/dL":
        return value / 0.323
    raise ValueError(f"unsupported conversion for {test_code}: {source_unit} -> {target_unit}")


def harmonize_row(row, ref_row):
    run_id = str(row["run_id"]).strip() if not pd.isna(row["run_id"]) else ""
    if run_id == "":
        return None, None, True

    parsed = parse_value(row["result_raw"])
    if parsed is None:
        return None, None, True

    target_unit = ref_row["target_unit"]
    plausible_low = float(ref_row["plausible_low"])
    plausible_high = float(ref_row["plausible_high"])
    reported_unit = str(row["reported_unit"]).strip()

    if reported_unit == "instrument_default":
        if plausible_low <= parsed <= plausible_high:
            return parsed, False, False
        for candidate_unit in str(ref_row["alternate_units"]).split("|"):
            candidate_unit = candidate_unit.strip()
            converted = convert_value(row["test_code"], parsed, candidate_unit, target_unit)
            if plausible_low <= converted <= plausible_high:
                return converted, True, False
        return parsed, False, False

    standardized = convert_value(row["test_code"], parsed, reported_unit, target_unit)
    converted = reported_unit != target_unit
    return standardized, converted, False


measurements = pd.read_csv(INPUT_LOG, dtype=str, keep_default_na=False)
reference = pd.read_csv(REFERENCE, dtype=str, keep_default_na=False)
reference["ref_key"] = reference["test_code"] + "||" + reference["qc_level"]
ref_map = reference.set_index("ref_key").to_dict(orient="index")

rows = []
for row in measurements.to_dict(orient="records"):
    ref_key = f'{row["test_code"]}||{row["qc_level"]}'
    if ref_key not in ref_map:
        continue
    ref_row = ref_map[ref_key]
    standardized, converted, excluded = harmonize_row(row, ref_row)
    rows.append(
        {
            "report_date": row["run_date"],
            "analyzer_id": row["analyzer_id"],
            "test_code": row["test_code"],
            "qc_level": row["qc_level"],
            "standard_name": ref_row["standard_name"],
            "target_unit": ref_row["target_unit"],
            "display_order": int(ref_row["display_order"]),
            "target_low": float(ref_row["target_low"]),
            "target_high": float(ref_row["target_high"]),
            "excluded": excluded,
            "converted": bool(converted) if not excluded else False,
            "standardized_value": standardized,
        }
    )

detail = pd.DataFrame(rows)
group_cols = ["report_date", "analyzer_id", "test_code", "qc_level", "standard_name", "target_unit", "display_order", "target_low", "target_high"]

report_rows = []
for group_key, group in detail.groupby(group_cols, sort=False):
    included = group[~group["excluded"]].copy()
    excluded_count = int(group["excluded"].sum())
    if included.empty:
        continue

    mean_value = included["standardized_value"].mean()
    rounded_mean = round(float(mean_value), 2)
    low = float(group_key[7])
    high = float(group_key[8])
    midpoint = (low + high) / 2.0
    bias_pct = ((rounded_mean - midpoint) / midpoint) * 100.0

    report_rows.append(
        {
            "report_date": group_key[0],
            "analyzer_id": group_key[1],
            "test_code": group_key[2],
            "qc_level": group_key[3],
            "standard_name": group_key[4],
            "target_unit": group_key[5],
            "included_run_count": int(len(included)),
            "converted_run_count": int(included["converted"].sum()),
            "excluded_run_count": excluded_count,
            "standardized_mean": f"{rounded_mean:.2f}",
            "target_midpoint": f"{midpoint:.2f}",
            "relative_target_bias_pct": f"{bias_pct:.2f}",
            "out_of_control": "true" if rounded_mean < low or rounded_mean > high else "false",
            "display_order": int(group_key[6]),
        }
    )

report = pd.DataFrame(report_rows)
report = report.sort_values(
    by=["report_date", "analyzer_id", "display_order", "qc_level"],
    kind="mergesort",
).reset_index(drop=True)

report = report[
    [
        "report_date",
        "analyzer_id",
        "test_code",
        "qc_level",
        "standard_name",
        "target_unit",
        "included_run_count",
        "converted_run_count",
        "excluded_run_count",
        "standardized_mean",
        "target_midpoint",
        "relative_target_bias_pct",
        "out_of_control",
    ]
]

report.to_csv(OUTPUT, index=False)
PY
