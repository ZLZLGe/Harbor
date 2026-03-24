import json
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("/root/highway_trip.csv")
OUTPUT_PATH = Path("/root/acc_mode_audit.csv")
SUMMARY_PATH = Path("/root/audit_summary.json")
SCRIPT_PATH = Path("/root/build_mode_audit.py")


def test_required_files_exist():
    assert INPUT_PATH.exists()
    assert SCRIPT_PATH.exists(), "build_mode_audit.py must exist"
    assert OUTPUT_PATH.exists(), "acc_mode_audit.csv must exist"
    assert SUMMARY_PATH.exists(), "audit_summary.json must exist"


def test_input_file_shape():
    df = pd.read_csv(INPUT_PATH)
    assert list(df.columns) == [
        "time_s",
        "road_phase",
        "ego_speed_mps",
        "lead_speed_mps",
        "lead_gap_m",
    ]
    assert len(df) == 1501
    assert df["time_s"].iloc[0] == 0.0
    assert df["time_s"].iloc[-1] == 150.0
    assert set(df["road_phase"].unique()) == {
        "open_lane",
        "steady_follow",
        "wide_gap",
        "cut_in_event",
        "clear_lane",
    }


def test_output_csv_columns_and_alignment():
    src = pd.read_csv(INPUT_PATH)
    out = pd.read_csv(OUTPUT_PATH)

    assert list(out.columns) == [
        "time_s",
        "road_phase",
        "ego_speed_mps",
        "lead_speed_mps",
        "lead_gap_m",
        "lead_present",
        "closing_speed_mps",
        "safe_gap_m",
        "gap_margin_m",
        "ttc_s",
        "mode",
        "gap_flag",
    ]
    assert len(out) == len(src)
    assert out["time_s"].equals(src["time_s"])
    assert out["road_phase"].equals(src["road_phase"])
    assert out["ego_speed_mps"].equals(src["ego_speed_mps"])


def test_mode_rules_and_selected_rows():
    out = pd.read_csv(OUTPUT_PATH)
    lead_present = out["lead_present"].astype(str).str.lower()

    first = out.iloc[0]
    assert lead_present.iloc[0] == "false"
    assert pd.isna(first["closing_speed_mps"])
    assert first["safe_gap_m"] == 10.0
    assert pd.isna(first["ttc_s"])
    assert first["mode"] == "cruise"
    assert first["gap_flag"] == "missing_lead"

    row_499 = out.iloc[499]
    assert lead_present.iloc[499] == "true"
    assert row_499["closing_speed_mps"] == 0.86
    assert row_499["safe_gap_m"] == 47.5
    assert row_499["gap_margin_m"] == -8.73
    assert row_499["ttc_s"] == 45.081
    assert row_499["mode"] == "follow"
    assert row_499["gap_flag"] == "tight"

    row_500 = out.iloc[500]
    assert row_500["closing_speed_mps"] == -0.27
    assert pd.isna(row_500["ttc_s"])
    assert row_500["mode"] == "follow"

    row_1200 = out.iloc[1200]
    assert row_1200["road_phase"] == "cut_in_event"
    assert row_1200["closing_speed_mps"] == 14.94
    assert row_1200["gap_margin_m"] == -14.48
    assert row_1200["ttc_s"] == 1.708
    assert row_1200["mode"] == "emergency"
    assert row_1200["gap_flag"] == "tight"

    last = out.iloc[-1]
    assert lead_present.iloc[-1] == "false"
    assert last["safe_gap_m"] == 55.0
    assert last["mode"] == "cruise"


def test_summary_metrics():
    with SUMMARY_PATH.open() as f:
        summary = json.load(f)

    assert summary == {
        "rows_total": 1501,
        "lead_present_rows": 1000,
        "lead_missing_rows": 501,
        "mode_counts": {
            "cruise": 501,
            "follow": 976,
            "emergency": 24,
        },
        "gap_flag_counts": {
            "missing_lead": 501,
            "tight": 607,
            "safe": 393,
        },
        "min_ttc_s": 0.178,
        "min_observed_gap_m": 1.95,
        "max_gap_deficit_m": 26.05,
        "first_emergency_time_s": 120.0,
    }
