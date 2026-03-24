import csv
import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd
import yaml


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
sys.path.insert(0, str(TASK_ROOT))


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class TestInputFiles:
    def test_input_assets_unchanged(self):
        policy = load_yaml(TASK_ROOT / "freezer_policy.yaml")
        assert policy["site"]["facility_id"] == "HK-COLD-03"
        assert policy["analysis"]["sample_interval_hours"] == 1
        assert list(policy["alarm_windows"].keys()) == ["day", "swing", "night"]
        assert policy["equipment_groups"]["produce_line"]["defrost"]["base_interval_hours"] == 8
        assert policy["equipment_groups"]["protein_line"]["max_temp_c"] == -15.5

        log = pd.read_csv(TASK_ROOT / "temperature_log.csv")
        assert len(log) == 96
        assert list(log.columns) == ["timestamp", "freezer_id", "temp_c", "door_open", "alarm_code"]
        assert sorted(log["freezer_id"].unique().tolist()) == ["FZ-A1", "FZ-A2", "FZ-B1", "FZ-B2"]


class TestPolicyTransferScript:
    def test_function_exists_and_returns_expected_shapes(self):
        spec = importlib.util.spec_from_file_location("policy_transfer", TASK_ROOT / "policy_transfer.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "build_defrost_policy")
        policy_output, summary_rows = module.build_defrost_policy(
            TASK_ROOT / "freezer_policy.yaml",
            TASK_ROOT / "temperature_log.csv",
        )

        assert isinstance(policy_output, dict)
        assert isinstance(summary_rows, list)
        assert policy_output["source_files"] == {
            "policy": "freezer_policy.yaml",
            "log": "temperature_log.csv",
        }
        assert len(summary_rows) == 6


class TestDefrostPolicy:
    def test_yaml_output(self):
        output = load_yaml(TASK_ROOT / "defrost_policy.yaml")
        assert list(output.keys()) == ["site", "source_files", "policy_recommendations"]
        assert output["site"] == {"facility_id": "HK-COLD-03", "timezone": "Asia/Hong_Kong"}
        assert output["source_files"] == {
            "policy": "freezer_policy.yaml",
            "log": "temperature_log.csv",
        }

        expected = {
            "FZ-A1": {
                "group": "produce_line",
                "schedule": {
                    "interval_hours": 6,
                    "duration_minutes": 40,
                    "preferred_window": "day",
                    "recommended_start": "06:30",
                },
                "analysis": {
                    "anomaly_periods": 2,
                    "total_anomaly_hours": 4,
                    "peak_temp_c": -15.1,
                    "peak_excursion_c": 0.9,
                    "door_open_hours": 3,
                    "inspection_priority": "review",
                    "trigger_codes": ["HIGH_TEMP"],
                },
            },
            "FZ-A2": {
                "group": "produce_line",
                "schedule": {
                    "interval_hours": 8,
                    "duration_minutes": 35,
                    "preferred_window": "night",
                    "recommended_start": "22:30",
                },
                "analysis": {
                    "anomaly_periods": 1,
                    "total_anomaly_hours": 2,
                    "peak_temp_c": -15.9,
                    "peak_excursion_c": 0.1,
                    "door_open_hours": 2,
                    "inspection_priority": "routine",
                    "trigger_codes": ["HIGH_TEMP"],
                },
            },
            "FZ-B1": {
                "group": "protein_line",
                "schedule": {
                    "interval_hours": 5,
                    "duration_minutes": 50,
                    "preferred_window": "swing",
                    "recommended_start": "14:30",
                },
                "analysis": {
                    "anomaly_periods": 2,
                    "total_anomaly_hours": 5,
                    "peak_temp_c": -12.9,
                    "peak_excursion_c": 2.6,
                    "door_open_hours": 2,
                    "inspection_priority": "urgent",
                    "trigger_codes": ["HIGH_TEMP"],
                },
            },
            "FZ-B2": {
                "group": "protein_line",
                "schedule": {
                    "interval_hours": 7,
                    "duration_minutes": 40,
                    "preferred_window": "day",
                    "recommended_start": "06:30",
                },
                "analysis": {
                    "anomaly_periods": 1,
                    "total_anomaly_hours": 2,
                    "peak_temp_c": -15.2,
                    "peak_excursion_c": 0.3,
                    "door_open_hours": 2,
                    "inspection_priority": "routine",
                    "trigger_codes": ["HIGH_TEMP", "SENSOR_CHECK"],
                },
            },
        }

        assert output["policy_recommendations"] == expected


class TestAnomalySummary:
    def test_summary_csv(self):
        with open(TASK_ROOT / "anomaly_summary.csv", "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        assert reader.fieldnames == [
            "freezer_id",
            "group_name",
            "start_time",
            "end_time",
            "duration_hours",
            "peak_temp_c",
            "door_open_hours",
            "window_name",
            "priority",
        ]

        expected_rows = [
            {
                "freezer_id": "FZ-A1",
                "group_name": "produce_line",
                "start_time": "2026-02-14T08:00:00",
                "end_time": "2026-02-14T09:00:00",
                "duration_hours": "2",
                "peak_temp_c": "-15.1",
                "door_open_hours": "2",
                "window_name": "day",
                "priority": "review",
            },
            {
                "freezer_id": "FZ-A1",
                "group_name": "produce_line",
                "start_time": "2026-02-14T15:00:00",
                "end_time": "2026-02-14T16:00:00",
                "duration_hours": "2",
                "peak_temp_c": "-15.2",
                "door_open_hours": "1",
                "window_name": "swing",
                "priority": "review",
            },
            {
                "freezer_id": "FZ-A2",
                "group_name": "produce_line",
                "start_time": "2026-02-14T04:00:00",
                "end_time": "2026-02-14T05:00:00",
                "duration_hours": "2",
                "peak_temp_c": "-15.9",
                "door_open_hours": "2",
                "window_name": "night",
                "priority": "routine",
            },
            {
                "freezer_id": "FZ-B1",
                "group_name": "protein_line",
                "start_time": "2026-02-14T12:00:00",
                "end_time": "2026-02-14T14:00:00",
                "duration_hours": "3",
                "peak_temp_c": "-12.9",
                "door_open_hours": "2",
                "window_name": "day",
                "priority": "urgent",
            },
            {
                "freezer_id": "FZ-B1",
                "group_name": "protein_line",
                "start_time": "2026-02-14T19:00:00",
                "end_time": "2026-02-14T20:00:00",
                "duration_hours": "2",
                "peak_temp_c": "-13.9",
                "door_open_hours": "0",
                "window_name": "swing",
                "priority": "urgent",
            },
            {
                "freezer_id": "FZ-B2",
                "group_name": "protein_line",
                "start_time": "2026-02-14T11:00:00",
                "end_time": "2026-02-14T12:00:00",
                "duration_hours": "2",
                "peak_temp_c": "-15.2",
                "door_open_hours": "2",
                "window_name": "day",
                "priority": "routine",
            },
        ]

        assert rows == expected_rows
