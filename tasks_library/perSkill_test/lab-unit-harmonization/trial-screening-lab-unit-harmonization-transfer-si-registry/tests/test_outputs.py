import os
import re

import pandas as pd


OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/trial_screening_labs_si.csv")

EXPECTED_COLUMNS = [
    "study_id",
    "country_code",
    "site_code",
    "subject_id",
    "screening_visit",
    "collection_date",
    "specimen_id",
    "registry_test_code",
    "registry_test_name",
    "standard_value",
    "standard_unit",
]

EXPECTED_SPECIMENS = [
    "SP-001",
    "SP-002",
    "SP-003",
    "SP-004",
    "SP-005",
    "SP-006",
    "SP-007",
    "SP-008",
    "SP-009",
    "SP-010",
    "SP-011",
    "SP-012",
    "SP-017",
    "SP-018",
    "SP-019",
]

EXPECTED_VALUES = {
    "SP-001": ("CREA", "167.96", "umol/L"),
    "SP-002": ("HGB", "112.00", "g/L"),
    "SP-004": ("CA", "2.30", "mmol/L"),
    "SP-006": ("GLU", "5.99", "mmol/L"),
    "SP-007": ("URATE", "416.36", "umol/L"),
    "SP-009": ("UREA", "27.13", "mmol/L"),
    "SP-011": ("CREA", "132.00", "umol/L"),
    "SP-012": ("ALB", "39.00", "g/L"),
    "SP-017": ("CA", "2.41", "mmol/L"),
    "SP-018": ("PHOS", "1.65", "mmol/L"),
    "SP-019": ("GLU", "6.40", "mmol/L"),
}

EXPECTED_NAME_BY_CODE = {
    "CREA": "Serum Creatinine",
    "UREA": "Urea Nitrogen",
    "HGB": "Hemoglobin",
    "ALB": "Albumin",
    "CA": "Calcium",
    "PHOS": "Phosphate",
    "URATE": "Uric Acid",
    "GLU": "Glucose",
    "K": "Potassium",
    "HCO3": "Bicarbonate",
}

EXPECTED_UNIT_BY_CODE = {
    "CREA": "umol/L",
    "UREA": "mmol/L",
    "HGB": "g/L",
    "ALB": "g/L",
    "CA": "mmol/L",
    "PHOS": "mmol/L",
    "URATE": "umol/L",
    "GLU": "mmol/L",
    "K": "mmol/L",
    "HCO3": "mmol/L",
}

NUMERIC_PATTERN = re.compile(r"^-?\d+\.\d{2}$")


def read_output():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE, dtype=str, keep_default_na=False)


def test_columns_and_sort_order():
    df = read_output()
    assert list(df.columns) == EXPECTED_COLUMNS
    sorted_df = df.sort_values(
        by=["collection_date", "site_code", "subject_id", "specimen_id"],
        kind="mergesort",
    ).reset_index(drop=True)
    assert df.equals(sorted_df)


def test_retained_specimens_match_contract():
    df = read_output()
    assert df["specimen_id"].tolist() == EXPECTED_SPECIMENS
    assert df["specimen_id"].is_unique


def test_numeric_format_and_no_dirty_tokens():
    df = read_output()
    values = df["standard_value"].tolist()
    assert all(NUMERIC_PATTERN.match(value) for value in values)
    assert all(value == value.strip() for value in values)
    assert all("," not in value for value in values)
    assert all("e" not in value.lower() for value in values)


def test_units_and_names_follow_registry_spec():
    df = read_output()
    for row in df.to_dict(orient="records"):
        code = row["registry_test_code"]
        assert row["registry_test_name"] == EXPECTED_NAME_BY_CODE[code]
        assert row["standard_unit"] == EXPECTED_UNIT_BY_CODE[code]


def test_key_conversions_cover_explicit_and_ambiguous_units():
    df = read_output().set_index("specimen_id")
    for specimen_id, (code, value, unit) in EXPECTED_VALUES.items():
        row = df.loc[specimen_id]
        assert row["registry_test_code"] == code
        assert row["standard_value"] == value
        assert row["standard_unit"] == unit
