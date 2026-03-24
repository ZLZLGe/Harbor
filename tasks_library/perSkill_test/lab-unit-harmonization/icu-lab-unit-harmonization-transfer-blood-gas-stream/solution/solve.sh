#!/bin/bash
set -euo pipefail

INPUT_FILE="${INPUT_FILE:-/root/environment/data/icu_blood_gas_stream_raw.csv}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/icu_blood_gas_harmonized.csv}"

INPUT_FILE="$INPUT_FILE" OUTPUT_FILE="$OUTPUT_FILE" python - <<'PY'
import os
import pandas as pd
import numpy as np

INPUT_FILE = os.environ["INPUT_FILE"]
OUTPUT_FILE = os.environ["OUTPUT_FILE"]

NUMERIC_COLUMNS = [
    "pH",
    "pCO2",
    "pO2",
    "lactate",
    "bicarbonate",
    "sodium",
    "potassium",
    "chloride",
    "ionized_calcium",
]

REFERENCE_RANGES = {
    "pH": (6.8, 7.8),
    "pCO2": (15.0, 100.0),
    "pO2": (25.0, 500.0),
    "lactate": (0.3, 20.0),
    "bicarbonate": (5.0, 45.0),
    "sodium": (110.0, 170.0),
    "potassium": (2.0, 8.0),
    "chloride": (70.0, 140.0),
    "ionized_calcium": (0.6, 2.0),
}

CONVERSION_FACTORS = {
    "pCO2": [1.0 / 0.133],
    "pO2": [1.0 / 0.133],
    "lactate": [1.0 / 9.01],
    "ionized_calcium": [0.25],
}


def parse_value(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none"}:
        return np.nan

    if "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return np.nan


def convert_if_needed(value, column):
    if pd.isna(value):
        return value

    lower, upper = REFERENCE_RANGES[column]
    if lower <= value <= upper:
        return value

    tolerance = (upper - lower) * 0.05
    for factor in CONVERSION_FACTORS.get(column, []):
        converted = value * factor
        if (lower - tolerance) <= converted <= (upper + tolerance):
            return min(max(converted, lower), upper)

    return value


df = pd.read_csv(INPUT_FILE, dtype=str)
column_order = list(df.columns)

for column in NUMERIC_COLUMNS:
    df[column] = df[column].apply(parse_value)

df = df.dropna(subset=NUMERIC_COLUMNS).copy()

for column in NUMERIC_COLUMNS:
    df[column] = df[column].apply(lambda value: convert_if_needed(value, column))
    df[column] = df[column].apply(lambda value: f"{value:.2f}")

df = df.sort_values(["encounter_id", "sample_time"], kind="stable").reset_index(drop=True)
df = df[column_order]
df.to_csv(OUTPUT_FILE, index=False)
PY
