import json
from pathlib import Path

import pandas as pd
import pandas.testing as pdt


TEMP_INPUT = Path("/root/temperature_log.csv")
DOOR_INPUT = Path("/root/door_events.csv")
SCRIPT_PATH = Path("/root/analyze_excursions.py")
OUTPUT_PATH = Path("/root/excursion_windows.csv")
SUMMARY_PATH = Path("/root/excursion_summary.json")


def test_required_files_exist():
    assert TEMP_INPUT.exists()
    assert DOOR_INPUT.exists()
    assert SCRIPT_PATH.exists(), "analyze_excursions.py must exist"
    assert OUTPUT_PATH.exists(), "excursion_windows.csv must exist"
    assert SUMMARY_PATH.exists(), "excursion_summary.json must exist"


def test_input_files_shape():
    temps = pd.read_csv(TEMP_INPUT)
    doors = pd.read_csv(DOOR_INPUT)

    assert list(temps.columns) == [
        "recorded_at",
        "compartment",
        "temperature_c",
        "upper_limit_c",
    ]
    assert len(temps) == 20
    assert set(temps["compartment"].unique()) == {"chilled", "frozen"}
    assert temps["temperature_c"].isna().sum() == 2
    assert temps["recorded_at"].iloc[0] == "2026-07-14T08:00"
    assert temps["recorded_at"].iloc[-1] == "2026-07-14T09:30"

    assert list(doors.columns) == ["event_time", "event_type"]
    assert doors.to_dict("records") == [
        {"event_time": "2026-07-14T08:15", "event_type": "open"},
        {"event_time": "2026-07-14T08:33", "event_type": "close"},
    ]


def test_output_windows_exact_match():
    output = pd.read_csv(OUTPUT_PATH, dtype={"door_open_during_window": str})

    expected = pd.DataFrame(
        [
            {
                "window_id": "EXC-001",
                "compartment": "chilled",
                "start_time": "2026-07-14T08:20",
                "end_time": "2026-07-14T08:50",
                "sample_count": 3,
                "imputed_sample_count": 1,
                "duration_minutes": 30,
                "limit_c": 5.0,
                "max_temperature_c": 5.8,
                "max_excursion_c": 0.8,
                "peak_recorded_at": "2026-07-14T08:30",
                "door_open_minutes": 13,
                "door_open_during_window": "true",
                "door_open_cycle_count": 1,
            },
            {
                "window_id": "EXC-002",
                "compartment": "chilled",
                "start_time": "2026-07-14T09:00",
                "end_time": "2026-07-14T09:30",
                "sample_count": 3,
                "imputed_sample_count": 0,
                "duration_minutes": 30,
                "limit_c": 5.0,
                "max_temperature_c": 5.5,
                "max_excursion_c": 0.5,
                "peak_recorded_at": "2026-07-14T09:10",
                "door_open_minutes": 0,
                "door_open_during_window": "false",
                "door_open_cycle_count": 0,
            },
            {
                "window_id": "EXC-003",
                "compartment": "frozen",
                "start_time": "2026-07-14T08:10",
                "end_time": "2026-07-14T08:40",
                "sample_count": 3,
                "imputed_sample_count": 0,
                "duration_minutes": 30,
                "limit_c": -15.0,
                "max_temperature_c": -13.9,
                "max_excursion_c": 1.1,
                "peak_recorded_at": "2026-07-14T08:30",
                "door_open_minutes": 18,
                "door_open_during_window": "true",
                "door_open_cycle_count": 1,
            },
            {
                "window_id": "EXC-004",
                "compartment": "frozen",
                "start_time": "2026-07-14T08:50",
                "end_time": "2026-07-14T09:20",
                "sample_count": 3,
                "imputed_sample_count": 1,
                "duration_minutes": 30,
                "limit_c": -15.0,
                "max_temperature_c": -14.1,
                "max_excursion_c": 0.9,
                "peak_recorded_at": "2026-07-14T09:10",
                "door_open_minutes": 0,
                "door_open_during_window": "false",
                "door_open_cycle_count": 0,
            },
        ]
    )

    assert list(output.columns) == list(expected.columns)
    pdt.assert_frame_equal(output, expected, check_dtype=False)


def test_summary_metrics():
    with SUMMARY_PATH.open() as handle:
        summary = json.load(handle)

    assert summary == {
        "window_count": 4,
        "affected_compartments": ["chilled", "frozen"],
        "windows_with_door_open": 2,
        "longest_window_minutes": 30,
        "worst_excursion_c": 1.1,
        "total_door_open_minutes_during_excursions": 31,
    }
