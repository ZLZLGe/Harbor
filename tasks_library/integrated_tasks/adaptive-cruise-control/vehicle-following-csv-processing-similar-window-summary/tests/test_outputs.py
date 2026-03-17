import importlib.util
import math
from pathlib import Path

import pandas as pd
import pytest


OUTPUT_COLUMNS = [
    "window_id",
    "window_type",
    "start_time_s",
    "end_time_s",
    "sample_count",
    "avg_ego_speed_mps",
    "min_gap_m",
    "valid_ttc_count",
    "avg_valid_ttc_s",
    "min_valid_ttc_s",
]

EXPECTED_ROWS = [
    {
        "window_id": 0,
        "window_type": "open_road",
        "start_time_s": 0.0,
        "end_time_s": 1.0,
        "sample_count": 3,
        "avg_ego_speed_mps": 18.5,
        "min_gap_m": math.nan,
        "valid_ttc_count": 0,
        "avg_valid_ttc_s": math.nan,
        "min_valid_ttc_s": math.nan,
    },
    {
        "window_id": 1,
        "window_type": "following",
        "start_time_s": 1.5,
        "end_time_s": 3.0,
        "sample_count": 4,
        "avg_ego_speed_mps": 20.75,
        "min_gap_m": 31.0,
        "valid_ttc_count": 4,
        "avg_valid_ttc_s": 18.364,
        "min_valid_ttc_s": 18.0,
    },
    {
        "window_id": 2,
        "window_type": "critical_gap",
        "start_time_s": 3.5,
        "end_time_s": 5.0,
        "sample_count": 4,
        "avg_ego_speed_mps": 21.575,
        "min_gap_m": 11.0,
        "valid_ttc_count": 4,
        "avg_valid_ttc_s": 2.308,
        "min_valid_ttc_s": 2.0,
    },
    {
        "window_id": 3,
        "window_type": "following",
        "start_time_s": 5.5,
        "end_time_s": 6.5,
        "sample_count": 3,
        "avg_ego_speed_mps": 20.0,
        "min_gap_m": 27.0,
        "valid_ttc_count": 1,
        "avg_valid_ttc_s": 135.0,
        "min_valid_ttc_s": 135.0,
    },
    {
        "window_id": 4,
        "window_type": "open_road",
        "start_time_s": 7.0,
        "end_time_s": 7.5,
        "sample_count": 2,
        "avg_ego_speed_mps": 19.25,
        "min_gap_m": math.nan,
        "valid_ttc_count": 0,
        "avg_valid_ttc_s": math.nan,
        "min_valid_ttc_s": math.nan,
    },
    {
        "window_id": 5,
        "window_type": "critical_gap",
        "start_time_s": 8.0,
        "end_time_s": 9.0,
        "sample_count": 3,
        "avg_ego_speed_mps": 18.0,
        "min_gap_m": 8.0,
        "valid_ttc_count": 2,
        "avg_valid_ttc_s": 1.527,
        "min_valid_ttc_s": 1.417,
    },
]
class TestInputs:
    def test_drive_telemetry_unchanged(self):
        df = pd.read_csv("/root/drive_telemetry.csv")
        assert list(df.columns) == [
            "time_s",
            "ego_speed_mps",
            "lead_speed_mps",
            "gap_m",
        ]
        assert len(df) == 19
        assert df["time_s"].iloc[0] == 0.0
        assert df["time_s"].iloc[-1] == 9.0


class TestScript:
    def test_script_exists_and_imports(self):
        script_path = Path("/root/summarize_following_windows.py")
        assert script_path.exists(), "summarize_following_windows.py must exist"

        spec = importlib.util.spec_from_file_location(
            "summarize_following_windows", script_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


class TestOutput:
    def test_output_exists(self):
        assert Path("/root/following_window_summary.csv").exists()

    def test_output_schema_and_rows(self):
        df = pd.read_csv("/root/following_window_summary.csv")
        assert list(df.columns) == OUTPUT_COLUMNS
        assert len(df) == len(EXPECTED_ROWS)
        assert df["window_id"].tolist() == [0, 1, 2, 3, 4, 5]
        assert df["window_type"].tolist() == [
            "open_road",
            "following",
            "critical_gap",
            "following",
            "open_road",
            "critical_gap",
        ]

    def test_output_values(self):
        df = pd.read_csv("/root/following_window_summary.csv")
        for index, expected in enumerate(EXPECTED_ROWS):
            actual = df.iloc[index].to_dict()
            assert int(actual["window_id"]) == expected["window_id"]
            assert actual["window_type"] == expected["window_type"]
            assert int(actual["sample_count"]) == expected["sample_count"]
            assert int(actual["valid_ttc_count"]) == expected["valid_ttc_count"]

            for key in [
                "start_time_s",
                "end_time_s",
                "avg_ego_speed_mps",
                "min_gap_m",
                "avg_valid_ttc_s",
                "min_valid_ttc_s",
            ]:
                if pd.isna(expected[key]):
                    assert pd.isna(actual[key])
                else:
                    assert actual[key] == pytest.approx(expected[key], abs=1e-3)

    def test_open_road_windows_leave_gap_and_ttc_blank(self):
        df = pd.read_csv("/root/following_window_summary.csv")
        open_road = df[df["window_type"] == "open_road"]
        assert open_road["min_gap_m"].isna().all()
        assert open_road["avg_valid_ttc_s"].isna().all()
        assert open_road["min_valid_ttc_s"].isna().all()
        assert (open_road["valid_ttc_count"] == 0).all()
