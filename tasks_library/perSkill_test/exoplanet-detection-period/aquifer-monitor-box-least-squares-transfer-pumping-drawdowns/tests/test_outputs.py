import csv
import re
from datetime import datetime
from pathlib import Path
from statistics import median

import astropy.units as u
import numpy as np
import pytest
from astropy.timeseries import BoxLeastSquares


DATA_PATH = Path("/root/data/well_drawdowns.tsv")
OUTPUT_PATH = Path("/root/output/pumping_drawdown_report.txt")
TITLE = "Aquifer Pumping Drawdown Report"
MIN_PERIOD = 10 * u.hour
MAX_PERIOD = 30 * u.hour
DURATIONS = np.linspace(45, 180, 19) * u.min


def load_wells():
    grouped = {}
    with DATA_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            grouped.setdefault(row["well_id"], []).append(
                (
                    datetime.strptime(row["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ"),
                    float(row["head_anomaly_m"]),
                )
            )

    return {
        well_id: sorted(points, key=lambda item: item[0])
        for well_id, points in grouped.items()
    }


def split_segments(mask):
    segments = []
    start = None
    for idx, flag in enumerate(mask):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            segments.append((start, idx))
            start = None
    if start is not None:
        segments.append((start, len(mask)))
    return segments


def analyze_well(points):
    start_time = points[0][0]
    elapsed_hours = np.array(
        [(timestamp - start_time).total_seconds() / 3600.0 for timestamp, _ in points],
        dtype=float,
    )
    values = np.array([value for _, value in points], dtype=float)

    model = BoxLeastSquares(elapsed_hours * u.hour, values)
    periodogram = model.autopower(
        DURATIONS,
        minimum_period=MIN_PERIOD,
        maximum_period=MAX_PERIOD,
        objective="snr",
    )

    best_idx = int(np.argmax(periodogram.power))
    period_hours = periodogram.period[best_idx].to_value(u.hour)
    duration_hours = periodogram.duration[best_idx].to_value(u.hour)
    reference_hours = periodogram.transit_time[best_idx].to_value(u.hour)
    peak_power = float(np.asarray(periodogram.power[best_idx]).reshape(-1)[0])

    phase = (
        (elapsed_hours - reference_hours + 0.5 * period_hours) % period_hours
    ) - 0.5 * period_hours
    mask = np.abs(phase) <= (0.5 * duration_hours + 1e-12)
    segments = split_segments(mask)
    depths = [abs(float(np.min(values[start:end]))) for start, end in segments]

    return {
        "drawdown_period_hours": period_hours,
        "median_drawdown_meters": float(median(depths)),
        "event_count": len(segments),
        "peak_power": peak_power,
    }


def derive_reference_report():
    wells = load_wells()
    assert len(wells) == 4, "测试数据应包含 4 口井"

    results = {well_id: analyze_well(points) for well_id, points in wells.items()}
    best_well_id, best = max(results.items(), key=lambda item: item[1]["peak_power"])

    return {
        "well_id": best_well_id,
        "drawdown_period_hours": f"{best['drawdown_period_hours']:.5f}",
        "median_drawdown_meters": f"{best['median_drawdown_meters']:.5f}",
        "event_count": str(best["event_count"]),
    }


@pytest.fixture(scope="module")
def parsed_output():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/pumping_drawdown_report.txt"
    raw = OUTPUT_PATH.read_text(encoding="utf-8")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    assert len(lines) == 5, "输出必须恰好包含 5 行非空文本"
    assert lines[0] == TITLE, "标题行不符合要求"

    patterns = {
        "well_id": r"^well_id: ([A-Za-z0-9-]+)$",
        "drawdown_period_hours": r"^drawdown_period_hours: (-?\d+\.\d{5})$",
        "median_drawdown_meters": r"^median_drawdown_meters: (-?\d+\.\d{5})$",
        "event_count": r"^event_count: ([1-9]\d*)$",
    }

    values = {}
    for key, line in zip(patterns, lines[1:]):
        match = re.fullmatch(patterns[key], line)
        assert match is not None, f"{key} 行格式不符合要求"
        values[key] = match.group(1)

    return values


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/pumping_drawdown_report.txt"


def test_output_schema(parsed_output):
    assert parsed_output["well_id"]
    assert float(parsed_output["drawdown_period_hours"]) > 0
    assert float(parsed_output["median_drawdown_meters"]) > 0
    assert int(parsed_output["event_count"]) > 0


def test_result_matches_full_bls_analysis(parsed_output):
    reference = derive_reference_report()
    assert parsed_output == reference
