import json

import numpy as np
import pandas as pd
import pytest
from netCDF4 import Dataset

CONFIG_PATH = "/root/config/intake_profile.json"
NC_PATH = "/root/data/silverwood_reservoir_output.nc"
REPORT_PATH = "/root/reports/intake_alerts.json"


def isoformat(dt: pd.Timestamp) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    return {
        "reservoir_name": str(config["reservoir_name"]),
        "simulation_start": pd.Timestamp(config["simulation_start"]),
        "lake_depth_m": float(config["lake_depth_m"]),
        "intake_depth_m": float(config["intake_depth_m"]),
        "alert_threshold_c": float(config["alert_threshold_c"]),
    }


def extract_series(start: pd.Timestamp, lake_depth_m: float, intake_depth_m: float) -> pd.DataFrame:
    with Dataset(NC_PATH, "r") as ds:
        time_values = np.array(ds.variables["time"][:], dtype=float)
        z = ds.variables["z"][:]
        temp = ds.variables["temp"][:]

    rows = []
    for time_index, hour_offset in enumerate(time_values):
        timestamp = start + pd.Timedelta(hours=float(hour_offset))
        heights = z[time_index, :, 0, 0]
        temperatures = temp[time_index, :, 0, 0]

        best = None
        for height_value, temp_value in zip(heights, temperatures):
            if np.ma.is_masked(height_value) or np.ma.is_masked(temp_value):
                continue
            depth_from_surface = lake_depth_m - float(height_value)
            if depth_from_surface < 0 or depth_from_surface > lake_depth_m:
                continue
            candidate = (
                abs(depth_from_surface - intake_depth_m),
                -depth_from_surface,
                float(temp_value),
            )
            if best is None or candidate[:2] < best[:2]:
                best = candidate

        if best is None:
            continue

        rows.append(
            {
                "timestamp": timestamp,
                "temperature_c": best[2],
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def build_alerts(series: pd.DataFrame, threshold_c: float, time_step_hours: float):
    alerts = []
    current = None

    for row in series.itertuples(index=False):
        is_alert = row.temperature_c > threshold_c
        if is_alert:
            if current is None:
                current = {
                    "start_time": row.timestamp,
                    "end_time": row.timestamp,
                    "sample_count": 1,
                    "peak_temperature_c": float(row.temperature_c),
                }
            else:
                current["end_time"] = row.timestamp
                current["sample_count"] += 1
                current["peak_temperature_c"] = max(current["peak_temperature_c"], float(row.temperature_c))
        elif current is not None:
            current["duration_hours"] = current["sample_count"] * time_step_hours
            alerts.append(current)
            current = None

    if current is not None:
        current["duration_hours"] = current["sample_count"] * time_step_hours
        alerts.append(current)

    normalized = []
    for alert in alerts:
        normalized.append(
            {
                "start_time": isoformat(alert["start_time"]),
                "end_time": isoformat(alert["end_time"]),
                "sample_count": int(alert["sample_count"]),
                "duration_hours": float(alert["duration_hours"]),
                "peak_temperature_c": float(alert["peak_temperature_c"]),
            }
        )

    normalized.sort(key=lambda item: item["start_time"])
    return normalized


def choose_longest_alert(alerts):
    if not alerts:
        return None

    return max(
        alerts,
        key=lambda item: (
            item["duration_hours"],
            item["peak_temperature_c"],
            -pd.Timestamp(item["start_time"]).timestamp(),
        ),
    )


def calculate_expected():
    config = load_config()
    series = extract_series(
        config["simulation_start"],
        config["lake_depth_m"],
        config["intake_depth_m"],
    )
    time_offsets = series["timestamp"].diff().dropna().dt.total_seconds().div(3600.0)
    time_step_hours = float(time_offsets.iloc[0]) if not time_offsets.empty else 0.0
    alerts = build_alerts(series, config["alert_threshold_c"], time_step_hours)
    peak_temperature_c = float(series["temperature_c"].max()) if not series.empty else float("nan")
    return {
        "reservoir_name": config["reservoir_name"],
        "intake_depth_m": config["intake_depth_m"],
        "alert_threshold_c": config["alert_threshold_c"],
        "time_step_hours": time_step_hours,
        "evaluated_sample_count": int(len(series)),
        "peak_temperature_c": peak_temperature_c,
        "alerts": alerts,
        "longest_alert": choose_longest_alert(alerts),
    }


def test_report_exists():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
    assert isinstance(report, dict)


def test_report_matches_contract_and_expected_values():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    expected = calculate_expected()
    required_keys = [
        "reservoir_name",
        "intake_depth_m",
        "alert_threshold_c",
        "time_step_hours",
        "evaluated_sample_count",
        "peak_temperature_c",
        "alerts",
        "longest_alert",
    ]

    for key in required_keys:
        assert key in report, f"missing key: {key}"

    assert isinstance(report["reservoir_name"], str)
    assert isinstance(report["intake_depth_m"], (int, float))
    assert isinstance(report["alert_threshold_c"], (int, float))
    assert isinstance(report["time_step_hours"], (int, float))
    assert isinstance(report["evaluated_sample_count"], int)
    assert isinstance(report["peak_temperature_c"], (int, float))
    assert isinstance(report["alerts"], list)
    assert report["longest_alert"] is None or isinstance(report["longest_alert"], dict)

    assert report["reservoir_name"] == expected["reservoir_name"]
    assert report["intake_depth_m"] == pytest.approx(expected["intake_depth_m"], abs=1e-6)
    assert report["alert_threshold_c"] == pytest.approx(expected["alert_threshold_c"], abs=1e-6)
    assert report["time_step_hours"] == pytest.approx(expected["time_step_hours"], abs=1e-6)
    assert report["evaluated_sample_count"] == expected["evaluated_sample_count"]
    assert report["peak_temperature_c"] == pytest.approx(expected["peak_temperature_c"], abs=5e-4)

    assert len(report["alerts"]) == len(expected["alerts"])
    required_alert_keys = {
        "start_time",
        "end_time",
        "sample_count",
        "duration_hours",
        "peak_temperature_c",
    }
    for actual, exp in zip(report["alerts"], expected["alerts"]):
        assert required_alert_keys.issubset(actual.keys())
        assert actual["start_time"] == exp["start_time"]
        assert actual["end_time"] == exp["end_time"]
        assert actual["sample_count"] == exp["sample_count"]
        assert actual["duration_hours"] == pytest.approx(exp["duration_hours"], abs=1e-6)
        assert actual["peak_temperature_c"] == pytest.approx(exp["peak_temperature_c"], abs=5e-4)

    if expected["longest_alert"] is None:
        assert report["longest_alert"] is None
    else:
        assert report["longest_alert"] is not None
        assert required_alert_keys.issubset(report["longest_alert"].keys())
        assert report["longest_alert"]["start_time"] == expected["longest_alert"]["start_time"]
        assert report["longest_alert"]["end_time"] == expected["longest_alert"]["end_time"]
        assert report["longest_alert"]["sample_count"] == expected["longest_alert"]["sample_count"]
        assert report["longest_alert"]["duration_hours"] == pytest.approx(
            expected["longest_alert"]["duration_hours"], abs=1e-6
        )
        assert report["longest_alert"]["peak_temperature_c"] == pytest.approx(
            expected["longest_alert"]["peak_temperature_c"], abs=5e-4
        )
