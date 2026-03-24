from pathlib import Path

import pandas as pd


def locate_task_root() -> Path:
    return Path(__file__).resolve().parents[1]


def locate_output_file() -> Path:
    candidates = [
        Path("/root/patient_alert_windows.csv"),
        locate_task_root() / "patient_alert_windows.csv",
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except PermissionError:
            continue
    raise AssertionError("patient_alert_windows.csv was not created")


class TestPatientAlertWindows:
    def test_output_matches_expected_windows(self):
        output_path = locate_output_file()
        df = pd.read_csv(output_path)

        expected = pd.DataFrame(
            [
                {
                    "patient_id": "P-100",
                    "alert_type": "high_heart_rate",
                    "alert_start": "2026-01-05 08:01",
                    "alert_end": "2026-01-05 08:04",
                    "extreme_value": 130.0,
                    "recovery_time_minutes": 1.0,
                },
                {
                    "patient_id": "P-100",
                    "alert_type": "low_spo2",
                    "alert_start": "2026-01-05 08:06",
                    "alert_end": "2026-01-05 08:08",
                    "extreme_value": 86.0,
                    "recovery_time_minutes": 1.0,
                },
                {
                    "patient_id": "P-200",
                    "alert_type": "high_heart_rate",
                    "alert_start": "2026-01-05 09:01",
                    "alert_end": "2026-01-05 09:03",
                    "extreme_value": 123.0,
                    "recovery_time_minutes": 1.0,
                },
                {
                    "patient_id": "P-200",
                    "alert_type": "low_spo2",
                    "alert_start": "2026-01-05 09:01",
                    "alert_end": "2026-01-05 09:02",
                    "extreme_value": 88.0,
                    "recovery_time_minutes": 2.0,
                },
                {
                    "patient_id": "P-200",
                    "alert_type": "high_heart_rate",
                    "alert_start": "2026-01-05 09:05",
                    "alert_end": "2026-01-05 09:08",
                    "extreme_value": 130.0,
                    "recovery_time_minutes": None,
                },
                {
                    "patient_id": "P-300",
                    "alert_type": "low_spo2",
                    "alert_start": "2026-01-05 10:01",
                    "alert_end": "2026-01-05 10:02",
                    "extreme_value": 87.0,
                    "recovery_time_minutes": 1.0,
                },
                {
                    "patient_id": "P-300",
                    "alert_type": "high_heart_rate",
                    "alert_start": "2026-01-05 10:04",
                    "alert_end": "2026-01-05 10:04",
                    "extreme_value": 122.0,
                    "recovery_time_minutes": 1.0,
                },
                {
                    "patient_id": "P-300",
                    "alert_type": "low_spo2",
                    "alert_start": "2026-01-05 10:05",
                    "alert_end": "2026-01-05 10:06",
                    "extreme_value": 88.0,
                    "recovery_time_minutes": 1.0,
                },
            ]
        )

        assert list(df.columns) == [
            "patient_id",
            "alert_type",
            "alert_start",
            "alert_end",
            "extreme_value",
            "recovery_time_minutes",
        ]

        df = df.sort_values(["patient_id", "alert_start", "alert_type"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(df, expected, check_dtype=False)

    def test_output_shape_and_blank_recovery(self):
        output_path = locate_output_file()
        df = pd.read_csv(output_path)

        assert len(df) == 8
        assert df.iloc[-1]["patient_id"] == "P-300"
        assert df["alert_type"].isin(["high_heart_rate", "low_spo2"]).all()

        trailing = df[
            (df["patient_id"] == "P-200")
            & (df["alert_type"] == "high_heart_rate")
            & (df["alert_start"] == "2026-01-05 09:05")
        ]
        assert len(trailing) == 1
        assert pd.isna(trailing.iloc[0]["recovery_time_minutes"])
