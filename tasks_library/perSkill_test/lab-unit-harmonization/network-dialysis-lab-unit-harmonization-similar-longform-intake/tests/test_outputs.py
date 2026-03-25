import math
import os
import re

import pandas as pd
from pandas.testing import assert_frame_equal


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
        if unit == "mg/dl":
            return numeric_value
        if unit in {"umol/l", "μmol/l"}:
            return numeric_value / 88.4
    elif analyte_code == "BUN":
        if unit == "mg/dl":
            return numeric_value
        if unit == "mmol/l":
            return numeric_value / 0.357
    elif analyte_code == "K":
        return numeric_value
    elif analyte_code == "CO2":
        return numeric_value
    elif analyte_code == "HGB":
        if unit == "g/dl":
            return numeric_value
        if unit == "g/l":
            return numeric_value / 10.0
        if unit == "mmol/l":
            return numeric_value / 0.6206
    elif analyte_code == "ALB":
        if unit == "g/dl":
            return numeric_value
        if unit == "g/l":
            return numeric_value / 10.0
    elif analyte_code == "CA":
        if unit == "mg/dl":
            return numeric_value
        if unit == "mmol/l":
            return numeric_value * 4.0
    elif analyte_code == "PHOS":
        if unit == "mg/dl":
            return numeric_value
        if unit == "mmol/l":
            return numeric_value / 0.323

    return pick_in_range(numeric_value, analyte_code, lo, hi)


def load_reference():
    reference = pd.read_csv(REFERENCE_FILE)
    reference["required"] = reference["required"].astype(str).str.lower().eq("true")
    return reference[reference["required"]].copy()


def build_expected_output():
    reference = load_reference()
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
    ordered_columns = META_COLUMNS + reference["output_column"].tolist()
    pivot = pivot.rename(columns=rename_map)[ordered_columns]
    pivot.columns.name = None

    for column in reference["output_column"]:
        pivot[column] = pivot[column].map(lambda value: f"{value:.2f}")

    return pivot


def read_output():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE, dtype=str, keep_default_na=False)


def test_columns_and_order():
    df = read_output()
    expected = build_expected_output()
    assert list(df.columns) == list(expected.columns)


def test_only_complete_encounters_remain():
    df = read_output()
    expected = build_expected_output()
    assert df["encounter_id"].tolist() == expected["encounter_id"].tolist()
    assert df["encounter_id"].is_unique


def test_numeric_format_is_fixed_two_decimals():
    df = read_output()
    numeric_columns = build_expected_output().columns[len(META_COLUMNS) :]
    pattern = re.compile(r"^-?\d+\.\d{2}$")
    for column in numeric_columns:
        values = df[column].tolist()
        assert all(pattern.match(value) for value in values), column
        assert all("," not in value for value in values), column
        assert all("e" not in value.lower() for value in values), column
        assert all(value == value.strip() for value in values), column


def test_exact_harmonized_values():
    actual = read_output()
    expected = build_expected_output()
    assert_frame_equal(actual, expected, check_dtype=False)
