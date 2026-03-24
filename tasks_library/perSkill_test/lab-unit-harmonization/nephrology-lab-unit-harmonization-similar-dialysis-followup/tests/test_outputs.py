#!/usr/bin/env python3
import hashlib
import os
import re

import pandas as pd
import pytest

OUTPUT_FILE = "/root/dialysis_followup_labs_harmonized.csv"

EXPECTED_COLUMNS = [
    "patient_code",
    "followup_month",
    "clinic_code",
    "access_type",
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

NUMERIC_COLUMNS = EXPECTED_COLUMNS[4:]

EXPECTED_ROW_COUNT = 108
EXPECTED_DIGEST = "8c720ee47efc7d498f848a16d20186bda927172a28f00f1a9b7414c020059b2d"
EXPECTED_MISSING_VISITS = {
    ("DX002", "2025-03"),
    ("DX004", "2025-02"),
    ("DX006", "2025-01"),
    ("DX009", "2025-04"),
    ("DX011", "2025-02"),
    ("DX013", "2025-03"),
    ("DX016", "2025-01"),
    ("DX018", "2025-04"),
    ("DX021", "2025-03"),
    ("DX024", "2025-02"),
    ("DX027", "2025-01"),
    ("DX030", "2025-04"),
}

EXPECTED_SAMPLES = {
    ("DX001", "2025-01"): {
        "clinic_code": "HZ01",
        "access_type": "CVC",
        "pre_bun": "52.48",
        "post_bun": "17.90",
        "scr": "6.40",
        "urate": "8.66",
        "k": "5.21",
        "hco3": "18.28",
        "hgb": "10.62",
        "ferritin": "316.94",
        "tsat": "21.28",
        "ca_total": "8.64",
        "phos": "6.13",
        "ipth": "954.41",
        "albumin": "3.86",
        "aluminum": "17.52",
    },
    ("DX014", "2025-04"): {
        "clinic_code": "HZ02",
        "access_type": "AVF",
        "pre_bun": "60.90",
        "post_bun": "23.45",
        "scr": "8.76",
        "urate": "6.29",
        "k": "4.93",
        "hco3": "23.22",
        "hgb": "7.40",
        "ferritin": "303.23",
        "tsat": "33.54",
        "ca_total": "8.68",
        "phos": "4.64",
        "ipth": "342.13",
        "albumin": "4.16",
        "aluminum": "9.18",
    },
    ("DX029", "2025-02"): {
        "clinic_code": "HZ02",
        "access_type": "AVF",
        "pre_bun": "35.00",
        "post_bun": "11.21",
        "scr": "10.91",
        "urate": "7.79",
        "k": "5.54",
        "hco3": "25.03",
        "hgb": "10.97",
        "ferritin": "1098.12",
        "tsat": "31.09",
        "ca_total": "8.80",
        "phos": "6.70",
        "ipth": "743.59",
        "albumin": "3.85",
        "aluminum": "18.87",
    },
}

EXPECTED_SUMMARY = {
    "scr_sum": 1033.27,
    "albumin_sum": 407.62,
    "hgb_mean": 10.482407407407406,
    "ca_total_mean": 8.905,
    "post_bun_median": 23.87,
}


def load_output():
    assert os.path.exists(OUTPUT_FILE), f"输出文件不存在: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE, dtype=str)


def canonical_digest(df):
    ordered = df.sort_values(["patient_code", "followup_month"]).reset_index(drop=True)
    text = ordered.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(text.encode()).hexdigest()


def test_columns_and_row_count():
    df = load_output()
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == EXPECTED_ROW_COUNT


def test_unique_visit_keys_and_removed_incomplete_rows():
    df = load_output()
    keys = set(zip(df["patient_code"], df["followup_month"]))
    assert len(keys) == len(df)
    assert EXPECTED_MISSING_VISITS.isdisjoint(keys)


def test_numeric_format_and_no_missing_values():
    df = load_output()
    pattern = re.compile(r"^-?\d+\.\d{2}$")

    for column in NUMERIC_COLUMNS:
        for value in df[column]:
            assert value == value.strip()
            assert value not in {"", "NaN", "None", "nan", "none"}
            assert "," not in value
            assert "e" not in value.lower()
            assert pattern.fullmatch(value), f"{column} 格式错误: {value}"


def test_sample_rows_match_expected_values():
    df = load_output()

    for key, expected in EXPECTED_SAMPLES.items():
        patient_code, followup_month = key
        row = df[(df["patient_code"] == patient_code) & (df["followup_month"] == followup_month)]
        assert len(row) == 1, f"未找到唯一样本行: {key}"
        record = row.iloc[0].to_dict()
        for column, expected_value in expected.items():
            assert record[column] == expected_value, f"{key} 的 {column} 不匹配"


def test_summary_metrics_match():
    df = load_output()
    numeric = df[NUMERIC_COLUMNS].astype(float)

    assert numeric["scr"].sum() == pytest.approx(EXPECTED_SUMMARY["scr_sum"], abs=1e-6)
    assert numeric["albumin"].sum() == pytest.approx(EXPECTED_SUMMARY["albumin_sum"], abs=1e-6)
    assert numeric["hgb"].mean() == pytest.approx(EXPECTED_SUMMARY["hgb_mean"], abs=1e-6)
    assert numeric["ca_total"].mean() == pytest.approx(EXPECTED_SUMMARY["ca_total_mean"], abs=1e-6)
    assert numeric["post_bun"].median() == pytest.approx(EXPECTED_SUMMARY["post_bun_median"], abs=1e-6)


def test_canonical_output_digest():
    df = load_output()
    assert canonical_digest(df) == EXPECTED_DIGEST
