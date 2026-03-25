import csv
import re
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
import pytest
from astropy.timeseries import BoxLeastSquares


DATA_PATH = Path("/root/data/bottling_lines.csv")
OUTPUT_PATH = Path("/root/output/cleaning_shutdown_report.csv")
EXPECTED_COLUMNS = [
    "line_id",
    "shutdown_period_minutes",
    "shutdown_duration_minutes",
    "downtime_fraction",
]
MIN_PERIOD = 140.0
MAX_PERIOD = 260.0
MIN_DURATION = 12.0
MAX_DURATION = 36.0
DURATIONS = np.linspace(MIN_DURATION, MAX_DURATION, 25) * u.min


def analyze_line(frame: pd.DataFrame) -> dict:
    time = frame["minute_index"].to_numpy() * u.min
    flux = frame["normalized_throughput"].to_numpy()

    model = BoxLeastSquares(time, flux)
    periodogram = model.autopower(
        DURATIONS,
        minimum_period=MIN_PERIOD * u.min,
        maximum_period=MAX_PERIOD * u.min,
        objective="snr",
    )

    best_idx = int(np.argmax(periodogram.power))
    period_minutes = periodogram.period[best_idx].to_value(u.min)
    duration_minutes = periodogram.duration[best_idx].to_value(u.min)

    return {
        "line_id": str(frame["line_id"].iloc[0]),
        "shutdown_period_minutes": float(period_minutes),
        "shutdown_duration_minutes": float(duration_minutes),
        "downtime_fraction": float(duration_minutes / period_minutes),
        "peak_power": float(periodogram.power[best_idx]),
    }


def expected_report() -> dict:
    df = pd.read_csv(DATA_PATH)
    candidates = [
        analyze_line(part.reset_index(drop=True))
        for _, part in df.groupby("line_id", sort=False)
    ]
    return max(candidates, key=lambda item: item["peak_power"])


def format_report(report: dict) -> dict:
    return {
        "line_id": report["line_id"],
        "shutdown_period_minutes": f'{report["shutdown_period_minutes"]:.5f}',
        "shutdown_duration_minutes": f'{report["shutdown_duration_minutes"]:.5f}',
        "downtime_fraction": f'{report["downtime_fraction"]:.5f}',
    }


@pytest.fixture(scope="module")
def output_row():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/cleaning_shutdown_report.csv"
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert reader.fieldnames == EXPECTED_COLUMNS, "CSV 列顺序或列名不符合要求"

    assert len(rows) == 1, "输出 CSV 只能包含 1 行数据"
    row = rows[0]
    return {
        "line_id": row["line_id"],
        "shutdown_period_minutes": row["shutdown_period_minutes"],
        "shutdown_duration_minutes": row["shutdown_duration_minutes"],
        "downtime_fraction": row["downtime_fraction"],
    }


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/cleaning_shutdown_report.csv"


def test_output_schema(output_row):
    assert output_row["line_id"], "line_id 不能为空"
    assert float(output_row["shutdown_period_minutes"]) > 0
    assert float(output_row["shutdown_duration_minutes"]) > 0
    assert 0 < float(output_row["downtime_fraction"]) < 1


def test_report_matches_highest_power_peak(output_row):
    expected = format_report(expected_report())

    assert output_row["line_id"] == expected["line_id"], "line_id 不是最高功率峰对应的产线"
    assert (
        output_row["shutdown_period_minutes"] == expected["shutdown_period_minutes"]
    ), "shutdown_period_minutes 不是最高功率峰对应的周期"
    assert (
        output_row["shutdown_duration_minutes"] == expected["shutdown_duration_minutes"]
    ), "shutdown_duration_minutes 不是最高功率峰对应的时长"
    assert (
        output_row["downtime_fraction"] == expected["downtime_fraction"]
    ), "downtime_fraction 与最高功率峰结果不一致"


def test_downtime_fraction_consistent(output_row):
    period_minutes = float(output_row["shutdown_period_minutes"])
    duration_minutes = float(output_row["shutdown_duration_minutes"])
    reconstructed = duration_minutes / period_minutes
    assert abs(float(output_row["downtime_fraction"]) - reconstructed) < 5e-5


def test_numeric_precision_written(output_row):
    for field_name in (
        "shutdown_period_minutes",
        "shutdown_duration_minutes",
        "downtime_fraction",
    ):
        text = output_row[field_name]
        match = re.fullmatch(r"-?\d+\.(\d{5})", text)
        assert match is not None, f"{field_name} 必须固定保留到小数点后 5 位"
