import os
import re

import pandas as pd


OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/analyzer_qc_drift_report.csv")

EXPECTED_COLUMNS = [
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

EXPECTED_ROWS = [
    {
        "report_date": "2025-02-10",
        "analyzer_id": "AX-100",
        "test_code": "CREA",
        "qc_level": "L1",
        "standard_name": "Serum Creatinine",
        "target_unit": "mg/dL",
        "included_run_count": "3",
        "converted_run_count": "1",
        "excluded_run_count": "1",
        "standardized_mean": "1.95",
        "target_midpoint": "2.00",
        "relative_target_bias_pct": "-2.50",
        "out_of_control": "false",
    },
    {
        "report_date": "2025-02-10",
        "analyzer_id": "AX-100",
        "test_code": "GLU",
        "qc_level": "L1",
        "standard_name": "Glucose",
        "target_unit": "mg/dL",
        "included_run_count": "3",
        "converted_run_count": "1",
        "excluded_run_count": "1",
        "standardized_mean": "103.33",
        "target_midpoint": "100.00",
        "relative_target_bias_pct": "3.33",
        "out_of_control": "false",
    },
    {
        "report_date": "2025-02-10",
        "analyzer_id": "AX-200",
        "test_code": "HGB",
        "qc_level": "L2",
        "standard_name": "Hemoglobin",
        "target_unit": "g/dL",
        "included_run_count": "3",
        "converted_run_count": "2",
        "excluded_run_count": "0",
        "standardized_mean": "12.26",
        "target_midpoint": "12.00",
        "relative_target_bias_pct": "2.17",
        "out_of_control": "false",
    },
    {
        "report_date": "2025-02-10",
        "analyzer_id": "AX-300",
        "test_code": "CA",
        "qc_level": "L1",
        "standard_name": "Calcium",
        "target_unit": "mg/dL",
        "included_run_count": "3",
        "converted_run_count": "2",
        "excluded_run_count": "1",
        "standardized_mean": "10.13",
        "target_midpoint": "9.20",
        "relative_target_bias_pct": "10.11",
        "out_of_control": "true",
    },
    {
        "report_date": "2025-02-11",
        "analyzer_id": "AX-100",
        "test_code": "CREA",
        "qc_level": "L1",
        "standard_name": "Serum Creatinine",
        "target_unit": "mg/dL",
        "included_run_count": "3",
        "converted_run_count": "1",
        "excluded_run_count": "0",
        "standardized_mean": "1.70",
        "target_midpoint": "2.00",
        "relative_target_bias_pct": "-15.00",
        "out_of_control": "true",
    },
    {
        "report_date": "2025-02-11",
        "analyzer_id": "AX-200",
        "test_code": "GLU",
        "qc_level": "L2",
        "standard_name": "Glucose",
        "target_unit": "mg/dL",
        "included_run_count": "3",
        "converted_run_count": "1",
        "excluded_run_count": "1",
        "standardized_mean": "197.67",
        "target_midpoint": "200.00",
        "relative_target_bias_pct": "-1.17",
        "out_of_control": "false",
    },
    {
        "report_date": "2025-02-11",
        "analyzer_id": "AX-200",
        "test_code": "PHOS",
        "qc_level": "L1",
        "standard_name": "Phosphorus",
        "target_unit": "mg/dL",
        "included_run_count": "3",
        "converted_run_count": "1",
        "excluded_run_count": "0",
        "standardized_mean": "4.53",
        "target_midpoint": "4.30",
        "relative_target_bias_pct": "5.35",
        "out_of_control": "false",
    },
    {
        "report_date": "2025-02-11",
        "analyzer_id": "AX-300",
        "test_code": "HGB",
        "qc_level": "L1",
        "standard_name": "Hemoglobin",
        "target_unit": "g/dL",
        "included_run_count": "3",
        "converted_run_count": "2",
        "excluded_run_count": "0",
        "standardized_mean": "9.26",
        "target_midpoint": "9.20",
        "relative_target_bias_pct": "0.65",
        "out_of_control": "false",
    },
]

NUMERIC_PATTERN = re.compile(r"^-?\d+\.\d{2}$")


def read_output():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE, dtype=str, keep_default_na=False)


def test_columns_and_row_order():
    df = read_output()
    assert list(df.columns) == EXPECTED_COLUMNS
    assert df[["report_date", "analyzer_id", "test_code", "qc_level"]].to_dict(orient="records") == [
        {k: row[k] for k in ["report_date", "analyzer_id", "test_code", "qc_level"]}
        for row in EXPECTED_ROWS
    ]


def test_numeric_fields_are_clean():
    df = read_output()
    for column in ["standardized_mean", "target_midpoint", "relative_target_bias_pct"]:
        values = df[column].tolist()
        assert all(NUMERIC_PATTERN.match(value) for value in values), column
        assert all(value == value.strip() for value in values), column
        assert all("," not in value for value in values), column
        assert all("e" not in value.lower() for value in values), column


def test_counts_and_flags_match_contract():
    df = read_output()
    for column in ["included_run_count", "converted_run_count", "excluded_run_count"]:
        assert all(value.isdigit() for value in df[column].tolist()), column
    assert set(df["out_of_control"].tolist()) <= {"true", "false"}
    flagged = df.loc[df["out_of_control"] == "true", ["analyzer_id", "test_code", "report_date"]]
    assert flagged.to_dict(orient="records") == [
        {"analyzer_id": "AX-300", "test_code": "CA", "report_date": "2025-02-10"},
        {"analyzer_id": "AX-100", "test_code": "CREA", "report_date": "2025-02-11"},
    ]


def test_bias_and_midpoint_are_self_consistent():
    df = read_output()
    for row in df.to_dict(orient="records"):
        mean_value = float(row["standardized_mean"])
        midpoint = float(row["target_midpoint"])
        actual_bias = round(((mean_value - midpoint) / midpoint) * 100, 2)
        assert f"{actual_bias:.2f}" == row["relative_target_bias_pct"]


def test_exact_report_rows():
    df = read_output()
    assert df.to_dict(orient="records") == EXPECTED_ROWS
