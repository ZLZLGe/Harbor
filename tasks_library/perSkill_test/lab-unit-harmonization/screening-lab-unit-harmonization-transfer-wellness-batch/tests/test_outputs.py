#!/usr/bin/env python3
import hashlib
import os
import re

import pandas as pd
import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/wellness_screening_labs_harmonized.csv")

EXPECTED_COLUMNS = [
    "employee_id",
    "employer_group",
    "screening_cycle",
    "exam_date",
    "vendor_name",
    "fasting_status",
    "age_band",
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

NUMERIC_COLUMNS = EXPECTED_COLUMNS[7:]

EXPECTED_ROW_COUNT = 20
EXPECTED_DIGEST = "03f285c05a14bc704ae30098155288e4ce0771b024bb1c38eedb237ff81d3c19"
EXPECTED_REMOVED_KEYS = {
    ("WB021", "2026-Q1"),
    ("WB022", "2026-Q1"),
    ("WB023", "2026-Q2"),
    ("WB024", "2026-Q2"),
}

EXPECTED_SAMPLES = {
    ("WB002", "2026-Q1"): {
        "vendor_name": "EuroCheck",
        "fasting_status": "fasting",
        "glucose": "108.00",
        "hba1c": "5.90",
        "total_cholesterol": "212.00",
        "ldl_cholesterol": "138.00",
        "hdl_cholesterol": "46.00",
        "triglycerides": "188.00",
        "tsh": "3.20",
        "free_t4": "1.01",
        "total_bilirubin": "0.90",
        "crp": "2.60",
    },
    ("WB006", "2026-Q1"): {
        "vendor_name": "EuroCheck",
        "fasting_status": "nonfasting",
        "glucose": "126.00",
        "hba1c": "6.50",
        "triglycerides": "286.00",
        "tsh": "0.30",
        "free_t4": "1.92",
        "alt": "64.00",
        "ggt": "96.00",
        "total_bilirubin": "1.80",
        "crp": "6.20",
    },
    ("WB011", "2026-Q2"): {
        "vendor_name": "PrimeCheck",
        "fasting_status": "nonfasting",
        "glucose": "111.00",
        "hba1c": "6.00",
        "total_cholesterol": "219.00",
        "ldl_cholesterol": "144.00",
        "hdl_cholesterol": "41.00",
        "triglycerides": "208.00",
        "crp": "3.10",
    },
    ("WB016", "2026-Q2"): {
        "vendor_name": "UnionLab",
        "fasting_status": "fasting",
        "glucose": "98.00",
        "hba1c": "5.50",
        "free_t4": "1.21",
        "total_bilirubin": "0.70",
        "crp": "1.10",
    },
    ("WB019", "2026-Q2"): {
        "vendor_name": "PrimeCheck",
        "fasting_status": "fasting",
        "glucose": "145.00",
        "hba1c": "7.10",
        "ldl_cholesterol": "182.00",
        "hdl_cholesterol": "34.00",
        "triglycerides": "322.00",
        "tsh": "7.30",
        "free_t4": "0.63",
        "alt": "78.00",
        "ggt": "126.00",
        "total_bilirubin": "2.40",
        "crp": "9.40",
    },
}

EXPECTED_COUNTS = {
    "fasting_rows": 13,
    "nonfasting_rows": 7,
    "q1_rows": 9,
    "q2_rows": 11,
    "orion_rows": 7,
    "harbor_rows": 7,
    "apex_rows": 6,
    "prediabetes": 8,
    "diabetes": 6,
    "high_ldl": 5,
    "low_hdl": 6,
    "high_tg": 11,
    "thyroid_followup": 9,
    "liver_signal": 10,
    "inflammation_signal": 12,
    "metabolic_pattern": 6,
}

EXPECTED_EMPLOYEE_SETS = {
    "high_risk_multidomain": {"WB003", "WB006", "WB009", "WB012", "WB015", "WB019"},
    "thyroid_plus_hypertriglyceridemia": {"WB003", "WB006", "WB009", "WB012", "WB015", "WB018", "WB019"},
}

EXPECTED_CYCLE_SUMMARY = {
    "q1_mean_glucose": 111.77777777777777,
    "q2_mean_glucose": 115.0909090909091,
    "q1_mean_crp": 3.611111111111111,
    "q2_mean_crp": 3.9454545454545453,
    "q1_median_ldl": 129.0,
    "q2_median_ldl": 144.0,
}

PHYSIOLOGIC_RANGES = {
    "glucose": (55.0, 260.0),
    "hba1c": (4.0, 12.0),
    "total_cholesterol": (100.0, 350.0),
    "ldl_cholesterol": (40.0, 250.0),
    "hdl_cholesterol": (20.0, 120.0),
    "triglycerides": (40.0, 500.0),
    "tsh": (0.1, 15.0),
    "free_t4": (0.4, 3.0),
    "alt": (5.0, 200.0),
    "ggt": (5.0, 200.0),
    "total_bilirubin": (0.2, 5.0),
    "crp": (0.1, 20.0),
}


def load_output():
    assert os.path.exists(OUTPUT_FILE), f"输出文件不存在: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE, dtype=str)


def canonical_digest(df):
    ordered = df.sort_values(["screening_cycle", "employee_id"]).reset_index(drop=True)
    text = ordered.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(text.encode()).hexdigest()


def test_schema_and_row_count():
    df = load_output()
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == EXPECTED_ROW_COUNT


def test_unique_sorted_keys_and_removed_incomplete_rows():
    df = load_output()
    keys = list(zip(df["employee_id"], df["screening_cycle"]))
    assert len(keys) == len(set(keys))
    assert EXPECTED_REMOVED_KEYS.isdisjoint(set(keys))
    assert list(zip(df["screening_cycle"], df["employee_id"])) == sorted(zip(df["screening_cycle"], df["employee_id"]))


def test_numeric_format_and_ranges():
    df = load_output()
    pattern = re.compile(r"^-?\d+\.\d{2}$")

    for column in NUMERIC_COLUMNS:
        lower, upper = PHYSIOLOGIC_RANGES[column]
        for value in df[column]:
            assert value == value.strip()
            assert value not in {"", "NaN", "nan", "None", "none"}
            assert "," not in value
            assert "e" not in value.lower()
            assert pattern.fullmatch(value), f"{column} 格式错误: {value}"
            numeric_value = float(value)
            assert lower <= numeric_value <= upper, f"{column} 超出生理范围: {value}"


def test_key_rows_match_expected_values():
    df = load_output()

    for key, expected in EXPECTED_SAMPLES.items():
        employee_id, screening_cycle = key
        row = df[(df["employee_id"] == employee_id) & (df["screening_cycle"] == screening_cycle)]
        assert len(row) == 1, f"未找到唯一样本行: {key}"
        record = row.iloc[0].to_dict()
        for column, expected_value in expected.items():
            assert record[column] == expected_value, f"{key} 的 {column} 不匹配"


def test_screening_prevalence_counts():
    df = load_output()
    numeric = df[NUMERIC_COLUMNS].astype(float)

    prediabetes = ((numeric["glucose"].between(100.0, 125.0)) | (numeric["hba1c"].between(5.7, 6.4))) & ~(
        (numeric["glucose"] >= 126.0) | (numeric["hba1c"] >= 6.5)
    )
    diabetes = (numeric["glucose"] >= 126.0) | (numeric["hba1c"] >= 6.5)
    high_ldl = numeric["ldl_cholesterol"] >= 160.0
    low_hdl = numeric["hdl_cholesterol"] < 40.0
    high_tg = numeric["triglycerides"] >= 200.0
    thyroid_followup = (numeric["tsh"] > 4.5) | (numeric["free_t4"] < 0.80) | (numeric["free_t4"] > 1.80)
    liver_signal = (numeric["alt"] >= 40.0) | (numeric["ggt"] >= 60.0) | (numeric["total_bilirubin"] >= 1.3)
    inflammation_signal = numeric["crp"] >= 3.0
    metabolic_pattern = (numeric["glucose"] >= 100.0) & (numeric["triglycerides"] >= 150.0) & (numeric["hdl_cholesterol"] < 40.0)

    assert int((df["fasting_status"] == "fasting").sum()) == EXPECTED_COUNTS["fasting_rows"]
    assert int((df["fasting_status"] == "nonfasting").sum()) == EXPECTED_COUNTS["nonfasting_rows"]
    assert int((df["screening_cycle"] == "2026-Q1").sum()) == EXPECTED_COUNTS["q1_rows"]
    assert int((df["screening_cycle"] == "2026-Q2").sum()) == EXPECTED_COUNTS["q2_rows"]
    assert int((df["employer_group"] == "OrionTech").sum()) == EXPECTED_COUNTS["orion_rows"]
    assert int((df["employer_group"] == "HarborRetail").sum()) == EXPECTED_COUNTS["harbor_rows"]
    assert int((df["employer_group"] == "ApexLogistics").sum()) == EXPECTED_COUNTS["apex_rows"]
    assert int(prediabetes.sum()) == EXPECTED_COUNTS["prediabetes"]
    assert int(diabetes.sum()) == EXPECTED_COUNTS["diabetes"]
    assert int(high_ldl.sum()) == EXPECTED_COUNTS["high_ldl"]
    assert int(low_hdl.sum()) == EXPECTED_COUNTS["low_hdl"]
    assert int(high_tg.sum()) == EXPECTED_COUNTS["high_tg"]
    assert int(thyroid_followup.sum()) == EXPECTED_COUNTS["thyroid_followup"]
    assert int(liver_signal.sum()) == EXPECTED_COUNTS["liver_signal"]
    assert int(inflammation_signal.sum()) == EXPECTED_COUNTS["inflammation_signal"]
    assert int(metabolic_pattern.sum()) == EXPECTED_COUNTS["metabolic_pattern"]


def test_followup_rosters():
    df = load_output()
    numeric = df[NUMERIC_COLUMNS].astype(float)

    prediabetes = ((numeric["glucose"].between(100.0, 125.0)) | (numeric["hba1c"].between(5.7, 6.4))) & ~(
        (numeric["glucose"] >= 126.0) | (numeric["hba1c"] >= 6.5)
    )
    diabetes = (numeric["glucose"] >= 126.0) | (numeric["hba1c"] >= 6.5)
    high_tg = numeric["triglycerides"] >= 200.0
    thyroid_followup = (numeric["tsh"] > 4.5) | (numeric["free_t4"] < 0.80) | (numeric["free_t4"] > 1.80)
    liver_signal = (numeric["alt"] >= 40.0) | (numeric["ggt"] >= 60.0) | (numeric["total_bilirubin"] >= 1.3)
    inflammation_signal = numeric["crp"] >= 3.0

    high_risk_multidomain = set(df.loc[diabetes & liver_signal & inflammation_signal, "employee_id"])
    thyroid_plus_hypertriglyceridemia = set(df.loc[(prediabetes | diabetes) & high_tg & thyroid_followup, "employee_id"])

    assert high_risk_multidomain == EXPECTED_EMPLOYEE_SETS["high_risk_multidomain"]
    assert thyroid_plus_hypertriglyceridemia == EXPECTED_EMPLOYEE_SETS["thyroid_plus_hypertriglyceridemia"]


def test_cycle_summary_metrics():
    df = load_output()
    numeric = df[NUMERIC_COLUMNS].astype(float)
    q1 = numeric[df["screening_cycle"] == "2026-Q1"]
    q2 = numeric[df["screening_cycle"] == "2026-Q2"]

    assert q1["glucose"].mean() == pytest.approx(EXPECTED_CYCLE_SUMMARY["q1_mean_glucose"], abs=1e-9)
    assert q2["glucose"].mean() == pytest.approx(EXPECTED_CYCLE_SUMMARY["q2_mean_glucose"], abs=1e-9)
    assert q1["crp"].mean() == pytest.approx(EXPECTED_CYCLE_SUMMARY["q1_mean_crp"], abs=1e-9)
    assert q2["crp"].mean() == pytest.approx(EXPECTED_CYCLE_SUMMARY["q2_mean_crp"], abs=1e-9)
    assert q1["ldl_cholesterol"].median() == pytest.approx(EXPECTED_CYCLE_SUMMARY["q1_median_ldl"], abs=1e-9)
    assert q2["ldl_cholesterol"].median() == pytest.approx(EXPECTED_CYCLE_SUMMARY["q2_median_ldl"], abs=1e-9)


def test_canonical_digest():
    df = load_output()
    assert canonical_digest(df) == EXPECTED_DIGEST
