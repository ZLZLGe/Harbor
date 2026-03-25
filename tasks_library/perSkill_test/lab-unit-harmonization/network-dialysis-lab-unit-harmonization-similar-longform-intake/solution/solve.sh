#!/bin/bash
set -euo pipefail

INPUT_FILE="${INPUT_FILE:-/root/environment/data/dialysis_intake_labs_long.csv}"
REFERENCE_FILE="${REFERENCE_FILE:-/root/environment/data/intake_panel_reference.csv}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/dialysis_intake_panel_harmonized.csv}"

python3 - <<'PY'
import os
import math
import pandas as pd

INPUT_FILE = os.environ.get("INPUT_FILE", "/root/environment/data/dialysis_intake_labs_long.csv")
REFERENCE_FILE = os.environ.get("REFERENCE_FILE", "/root/environment/data/intake_panel_reference.csv")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/dialysis_intake_panel_harmonized.csv")

META_COLUMNS = ["facility_code", "patient_id", "encounter_id", "intake_date"]


def parse_numeric(raw_value):
    if pd.isna(raw_value):
        return None
    text = str(raw_value).strip()
    if text == "":
        return None
    text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        return None
    if math.isnan(value):
        return None
    return value


def normalize_unit(unit):
    if pd.isna(unit):
        return ""
    return str(unit).strip().lower().replace("µ", "u")


def pick_in_range(value, analyte_code, lo, hi):
    converters = {
        "CREAT": [lambda x: x, lambda x: x / 88.4],
        "BUN": [lambda x: x, lambda x: x / 0.357],
        "K": [lambda x: x],
        "CO2": [lambda x: x],
        "HGB": [lambda x: x, lambda x: x / 10.0, lambda x: x / 0.6206],
        "ALB": [lambda x: x, lambda x: x / 10.0],
        "CA": [lambda x: x, lambda x: x * 4.0],
        "PHOS": [lambda x: x, lambda x: x / 0.323],
    }
    for converter in converters[analyte_code]:
        candidate = converter(value)
        if lo <= candidate <= hi:
            return candidate
    return value


def convert_value(analyte_code, numeric_value, reported_unit, lo, hi):
    unit = normalize_unit(reported_unit)
    if analyte_code == "CREAT":
        if unit in {"mg/dl"}:
            return numeric_value
        if unit in {"umol/l", "μmol/l"}:
            return numeric_value / 88.4
    elif analyte_code == "BUN":
        if unit in {"mg/dl"}:
            return numeric_value
        if unit in {"mmol/l"}:
            return numeric_value / 0.357
    elif analyte_code == "K":
        return numeric_value
    elif analyte_code == "CO2":
        return numeric_value
    elif analyte_code == "HGB":
        if unit in {"g/dl"}:
            return numeric_value
        if unit in {"g/l"}:
            return numeric_value / 10.0
        if unit in {"mmol/l"}:
            return numeric_value / 0.6206
    elif analyte_code == "ALB":
        if unit in {"g/dl"}:
            return numeric_value
        if unit in {"g/l"}:
            return numeric_value / 10.0
    elif analyte_code == "CA":
        if unit in {"mg/dl"}:
            return numeric_value
        if unit in {"mmol/l"}:
            return numeric_value * 4.0
    elif analyte_code == "PHOS":
        if unit in {"mg/dl"}:
            return numeric_value
        if unit in {"mmol/l"}:
            return numeric_value / 0.323

    return pick_in_range(numeric_value, analyte_code, lo, hi)


reference = pd.read_csv(REFERENCE_FILE)
reference["required"] = reference["required"].astype(str).str.lower().eq("true")
reference = reference[reference["required"]].copy()

raw = pd.read_csv(INPUT_FILE, dtype=str, keep_default_na=False)
raw = raw[raw["analyte_code"].isin(reference["analyte_code"])].copy()
raw["parsed_value"] = raw["result_value_raw"].apply(parse_numeric)

rules = reference.set_index("analyte_code").to_dict(orient="index")
raw["harmonized_value"] = raw.apply(
    lambda row: (
        None
        if row["parsed_value"] is None
        else convert_value(
            row["analyte_code"],
            row["parsed_value"],
            row["reported_unit"],
            float(rules[row["analyte_code"]]["conventional_min"]),
            float(rules[row["analyte_code"]]["conventional_max"]),
        )
    ),
    axis=1,
)

pivot = raw.pivot_table(
    index=META_COLUMNS,
    columns="analyte_code",
    values="harmonized_value",
    aggfunc="first",
    sort=False,
).reset_index()

required_codes = reference["analyte_code"].tolist()
pivot = pivot.dropna(subset=required_codes).copy()
pivot = pivot.sort_values(["intake_date", "encounter_id"]).reset_index(drop=True)

rename_map = dict(zip(reference["analyte_code"], reference["output_column"]))
pivot = pivot.rename(columns=rename_map)
ordered_columns = META_COLUMNS + reference["output_column"].tolist()
pivot = pivot[ordered_columns]

for column in reference["output_column"]:
    pivot[column] = pivot[column].map(lambda value: f"{value:.2f}")

pivot.to_csv(OUTPUT_FILE, index=False)
PY
