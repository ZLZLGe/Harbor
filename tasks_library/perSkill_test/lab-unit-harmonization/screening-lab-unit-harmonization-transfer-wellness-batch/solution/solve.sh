#!/bin/bash
set -euo pipefail

INPUT_FILE="/root/environment/data/wellness_screening_labs_raw.csv"
GUIDE_FILE="/root/environment/data/wellness_screening_column_guide.csv"
VENDOR_UNIT_FILE="/root/environment/data/wellness_screening_vendor_unit_defaults.csv"
OUTPUT_FILE="/root/wellness_screening_labs_harmonized.csv"

python3 - <<'PY'
import pandas as pd

INPUT_FILE = "/root/environment/data/wellness_screening_labs_raw.csv"
GUIDE_FILE = "/root/environment/data/wellness_screening_column_guide.csv"
VENDOR_UNIT_FILE = "/root/environment/data/wellness_screening_vendor_unit_defaults.csv"
OUTPUT_FILE = "/root/wellness_screening_labs_harmonized.csv"

NON_NUMERIC_COLUMNS = [
    "employee_id",
    "employer_group",
    "screening_cycle",
    "exam_date",
    "vendor_name",
    "fasting_status",
    "age_band",
]

NUMERIC_COLUMNS = [
    "glucose",
    "hba1c",
    "total_cholesterol",
    "ldl_cholesterol",
    "hdl_cholesterol",
    "triglycerides",
    "tsh",
    "free_t4",
    "alt",
    "ggt",
    "total_bilirubin",
    "crp",
]


def parse_value(value):
    if pd.isna(value):
        return pd.NA

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none"}:
        return pd.NA

    if "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return pd.NA


def convert_value(column, reported_unit, value):
    if pd.isna(value):
        return value

    if column == "glucose" and reported_unit == "mmol/L":
        return value / 0.0555
    if column in {"total_cholesterol", "ldl_cholesterol", "hdl_cholesterol"} and reported_unit == "mmol/L":
        return value / 0.0259
    if column == "triglycerides" and reported_unit == "mmol/L":
        return value / 0.0113
    if column == "free_t4" and reported_unit == "pmol/L":
        return value / 12.87
    if column == "total_bilirubin" and reported_unit == "umol/L":
        return value / 17.1
    if column == "crp" and reported_unit == "mg/dL":
        return value * 10.0
    return value


df = pd.read_csv(INPUT_FILE, dtype=str)
guide = pd.read_csv(GUIDE_FILE)
vendor_units = pd.read_csv(VENDOR_UNIT_FILE)

unit_lookup = {
    (row.vendor_name, row.column_name): row.reported_unit
    for row in vendor_units.itertuples(index=False)
}
range_lookup = {
    row.column_name: (float(row.min_plausible), float(row.max_plausible))
    for row in guide.itertuples(index=False)
}

for column in NUMERIC_COLUMNS:
    df[column] = df[column].map(parse_value)

df = df.dropna(subset=NUMERIC_COLUMNS).copy()

for column in NUMERIC_COLUMNS:
    df[column] = [
        convert_value(column, unit_lookup[(vendor_name, column)], value)
        for vendor_name, value in zip(df["vendor_name"], df[column])
    ]

for column in NUMERIC_COLUMNS:
    lower, upper = range_lookup[column]
    mask = df[column].between(lower, upper)
    if not bool(mask.all()):
        raise ValueError(f"{column} 存在超出目标范围的结果")
    df[column] = df[column].map(lambda value: f"{value:.2f}")

df = df[NON_NUMERIC_COLUMNS + NUMERIC_COLUMNS].sort_values(
    ["screening_cycle", "employee_id"]
).reset_index(drop=True)

df.to_csv(OUTPUT_FILE, index=False)
PY
