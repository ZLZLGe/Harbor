#!/bin/bash
set -euo pipefail

cat > /tmp/harmonize_dialysis_followup.py <<'PY'
#!/usr/bin/env python3
import pandas as pd
import numpy as np

INPUT_FILE = "/root/environment/data/dialysis_followup_labs_raw.csv"
OUTPUT_FILE = "/root/dialysis_followup_labs_harmonized.csv"

IDENTITY_COLUMNS = ["patient_code", "followup_month", "clinic_code", "access_type"]
NUMERIC_COLUMNS = [
    "pre_bun",
    "post_bun",
    "scr",
    "urate",
    "k",
    "hco3",
    "hgb",
    "ferritin",
    "tsat",
    "ca_total",
    "phos",
    "ipth",
    "albumin",
    "aluminum",
]

REFERENCE_RANGES = {
    "pre_bun": (20.0, 160.0),
    "post_bun": (5.0, 60.0),
    "scr": (2.0, 25.0),
    "urate": (2.0, 15.0),
    "k": (2.0, 8.0),
    "hco3": (10.0, 40.0),
    "hgb": (5.0, 15.0),
    "ferritin": (10.0, 2500.0),
    "tsat": (0.0, 100.0),
    "ca_total": (6.0, 12.0),
    "phos": (2.0, 10.0),
    "ipth": (50.0, 2000.0),
    "albumin": (2.0, 6.0),
    "aluminum": (5.0, 120.0),
}

CONVERSION_FACTORS = {
    "scr": [1 / 88.4],
    "urate": [1 / 59.48],
    "hgb": [0.1],
    "ca_total": [4.0, 2.0],
    "albumin": [0.1],
    "aluminum": [1 / 0.0371],
}


def parse_value(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none"}:
        return np.nan

    text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return np.nan


def harmonize_value(column, value):
    if pd.isna(value):
        return value

    low, high = REFERENCE_RANGES[column]
    if low <= value <= high:
        return value

    for factor in CONVERSION_FACTORS.get(column, []):
        converted = value * factor
        if low <= converted <= high:
            return converted

    return value


def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)

    for column in NUMERIC_COLUMNS:
        df[column] = df[column].map(parse_value)

    df = df.dropna(subset=NUMERIC_COLUMNS).copy()

    for column in NUMERIC_COLUMNS:
        df[column] = df[column].map(lambda value: harmonize_value(column, value))
        df[column] = df[column].map(lambda value: f"{value:.2f}")

    df = df[IDENTITY_COLUMNS + NUMERIC_COLUMNS]
    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
PY

python3 /tmp/harmonize_dialysis_followup.py
