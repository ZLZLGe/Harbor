import json
import re
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from astropy.timeseries import BoxLeastSquares


DATA_PATH = Path("/root/data/survey_candidates.csv")
OUTPUT_PATH = Path("/root/output/transit_candidate_summary.json")
MIN_PERIOD = 1.5 * u.day
MAX_PERIOD = 8.0 * u.day
DURATIONS = np.linspace(1.5, 5.5, 24) * u.hour
EXPECTED_KEYS = {"star_id", "period_days", "duration_hours", "depth_ppt", "peak_power"}


def scalar(value: object) -> float:
    if hasattr(value, "value"):
        value = value.value
    array = np.asarray(value)
    return float(array.reshape(-1)[0])


def load_rows():
    return np.genfromtxt(DATA_PATH, delimiter=",", names=True, dtype=None, encoding="utf-8")


def analyze_star(rows, star_id: str):
    mask = rows["star_id"] == star_id
    time = rows["time_days"][mask] * u.day
    flux = rows["flux"][mask]
    flux_err = rows["flux_err"][mask]

    model = BoxLeastSquares(time, flux, dy=flux_err)
    periodogram = model.autopower(
        DURATIONS,
        minimum_period=MIN_PERIOD,
        maximum_period=MAX_PERIOD,
        objective="snr",
    )

    best_idx = int(np.argmax(periodogram.power))
    period = periodogram.period[best_idx]
    duration = periodogram.duration[best_idx]
    transit_time = periodogram.transit_time[best_idx]
    peak_power = float(periodogram.power[best_idx])
    stats = model.compute_stats(period, duration, transit_time)

    return {
        "star_id": star_id,
        "period_days": period.to_value(u.day),
        "duration_hours": duration.to_value(u.hour),
        "depth_ppt": abs(scalar(stats["depth"])) * 1000.0,
        "peak_power": peak_power,
    }


def expected_best_candidate():
    rows = load_rows()
    candidates = [analyze_star(rows, str(star_id)) for star_id in np.unique(rows["star_id"])]
    return max(candidates, key=lambda item: item["peak_power"])


@pytest.fixture(scope="module")
def result():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/transit_candidate_summary.json"
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/output/transit_candidate_summary.json"


def test_output_schema(result):
    assert isinstance(result, dict), "输出必须是 JSON 对象"
    assert set(result.keys()) == EXPECTED_KEYS, "输出对象只能包含题目要求的 5 个键"
    assert isinstance(result["star_id"], str) and result["star_id"], "star_id 必须是非空字符串"

    for key in ("period_days", "duration_hours", "depth_ppt", "peak_power"):
        assert isinstance(result[key], (int, float)), f"{key} 必须是数值"

    assert result["period_days"] > 0
    assert result["duration_hours"] > 0
    assert result["depth_ppt"] > 0
    assert result["peak_power"] > 0


def test_best_candidate_matches_search(result):
    expected = expected_best_candidate()

    assert result["star_id"] == expected["star_id"], "star_id 不是全局最高功率峰对应的目标"
    assert abs(result["period_days"] - expected["period_days"]) < 0.03
    assert abs(result["duration_hours"] - expected["duration_hours"]) < 0.6
    assert abs(result["depth_ppt"] - expected["depth_ppt"]) < 1.5
    assert abs(result["peak_power"] - expected["peak_power"]) < max(0.15, 0.03 * expected["peak_power"])


def test_numeric_precision_written():
    raw = OUTPUT_PATH.read_text(encoding="utf-8")
    for key in ("period_days", "duration_hours", "depth_ppt", "peak_power"):
        match = re.search(rf'"{key}"\s*:\s*(-?\d+(?:\.(\d+))?)', raw)
        assert match is not None, f"找不到字段 {key}"
        decimals = match.group(2) or ""
        assert len(decimals) <= 5, f"{key} 需要保留到小数点后 5 位以内"
