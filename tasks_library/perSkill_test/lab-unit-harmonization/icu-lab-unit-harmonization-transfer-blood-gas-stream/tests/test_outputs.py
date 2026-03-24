#!/usr/bin/env python3
import os
import re

import pandas as pd
import pytest

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/icu_blood_gas_harmonized.csv")

EXPECTED_COLUMNS = [
    "encounter_id",
    "sample_time",
    "specimen_source",
    "vent_support",
    "device_id",
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

NUMERIC_COLUMNS = EXPECTED_COLUMNS[5:]

EXPECTED_REMOVED_KEYS = {
    ("A1001", "2026-02-14T10:00"),
    ("A1002", "2026-02-18T09:00"),
    ("A1004", "2026-02-25T17:00"),
}

EXPECTED_SAMPLE_ROWS = {
    ("A1001", "2026-02-14T08:00"): {
        "specimen_source": "arterial",
        "vent_support": "VC",
        "device_id": "BG01",
        "pH": "7.21",
        "pCO2": "55.00",
        "pO2": "68.00",
        "lactate": "4.80",
        "bicarbonate": "21.00",
        "sodium": "138.00",
        "potassium": "4.90",
        "chloride": "103.00",
        "ionized_calcium": "1.06",
    },
    ("A1002", "2026-02-18T03:20"): {
        "pCO2": "24.00",
        "pO2": "92.00",
        "lactate": "18.92",
        "bicarbonate": "8.00",
        "ionized_calcium": "1.14",
    },
    ("A1003", "2026-02-22T01:10"): {
        "pCO2": "62.00",
        "pO2": "58.00",
        "lactate": "15.32",
        "ionized_calcium": "1.03",
    },
    ("A1004", "2026-02-25T09:15"): {
        "pCO2": "50.00",
        "pO2": "74.00",
        "lactate": "6.20",
        "chloride": "107.00",
        "ionized_calcium": "0.98",
    },
}

EXPECTED_METRICS = {
    "high_lactate_count": 9,
    "respiratory_acid_count": 6,
    "arterial_low_po2_count": 5,
    "low_bicarbonate_count": 3,
    "low_ionized_calcium_count": 1,
    "acidemia_with_hyperlactatemia_count": 8,
}

EXPECTED_LACTATE_DELTA = {
    "A1001": -1.90,
    "A1002": -17.52,
    "A1003": -14.22,
    "A1004": -3.40,
}

EXPECTED_MIN_PH = {
    "A1001": 7.21,
    "A1002": 7.11,
    "A1003": 7.29,
    "A1004": 7.18,
}

PHYSIOLOGIC_RANGES = {
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


def load_output():
    assert os.path.exists(OUTPUT_FILE), f"输出文件不存在: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE, dtype=str)


def test_schema_and_row_count():
    df = load_output()
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 12


def test_removed_incomplete_rows_and_sorted_stream():
    df = load_output()
    keys = list(zip(df["encounter_id"], df["sample_time"]))
    assert len(keys) == len(set(keys))
    assert EXPECTED_REMOVED_KEYS.isdisjoint(set(keys))
    assert keys == sorted(keys)


def test_numeric_format_and_range():
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


def test_key_rows_match_expected_conversions():
    df = load_output()

    for key, expected in EXPECTED_SAMPLE_ROWS.items():
        encounter_id, sample_time = key
        row = df[(df["encounter_id"] == encounter_id) & (df["sample_time"] == sample_time)]
        assert len(row) == 1, f"未找到唯一样本行: {key}"
        record = row.iloc[0].to_dict()
        for column, expected_value in expected.items():
            assert record[column] == expected_value, f"{key} 的 {column} 不匹配"


def test_acid_base_signal_metrics():
    df = load_output()
    numeric = df[NUMERIC_COLUMNS].astype(float)

    assert int((numeric["lactate"] > 2.0).sum()) == EXPECTED_METRICS["high_lactate_count"]
    assert int((numeric["pCO2"] > 45.0).sum()) == EXPECTED_METRICS["respiratory_acid_count"]
    assert int(((df["specimen_source"] == "arterial") & (numeric["pO2"] < 80.0)).sum()) == EXPECTED_METRICS["arterial_low_po2_count"]
    assert int((numeric["bicarbonate"] < 18.0).sum()) == EXPECTED_METRICS["low_bicarbonate_count"]
    assert int((numeric["ionized_calcium"] < 1.0).sum()) == EXPECTED_METRICS["low_ionized_calcium_count"]
    assert int(((numeric["pH"] < 7.35) & (numeric["lactate"] > 2.0)).sum()) == EXPECTED_METRICS["acidemia_with_hyperlactatemia_count"]


@pytest.mark.parametrize("encounter_id, expected_delta", EXPECTED_LACTATE_DELTA.items())
def test_lactate_trend_by_encounter(encounter_id, expected_delta):
    df = load_output()
    encounter_df = df[df["encounter_id"] == encounter_id].sort_values("sample_time")
    lactate = encounter_df["lactate"].astype(float)
    observed = round(lactate.iloc[-1] - lactate.iloc[0], 2)
    assert observed == pytest.approx(expected_delta, abs=1e-6)


@pytest.mark.parametrize("encounter_id, expected_min_ph", EXPECTED_MIN_PH.items())
def test_nadir_ph_by_encounter(encounter_id, expected_min_ph):
    df = load_output()
    encounter_df = df[df["encounter_id"] == encounter_id]
    observed = encounter_df["pH"].astype(float).min()
    assert observed == pytest.approx(expected_min_ph, abs=1e-6)
