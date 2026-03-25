import json
from pathlib import Path


OUTPUT_PATH = Path("/root/sector_ephemeris.json")
EXPECTED_PERIOD = 4.23791
EXPECTED_EPOCH = 2201.14913
PERIOD_TOLERANCE = 0.01
EPOCH_TOLERANCE = 0.05
EXPECTED_KEYS = {"orbital_period_days", "reference_mid_transit_time_bkjd"}


def load_output():
    assert OUTPUT_PATH.exists(), "缺少 /root/sector_ephemeris.json"
    with OUTPUT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/sector_ephemeris.json"


def test_output_schema():
    payload = load_output()
    assert isinstance(payload, dict), "输出必须是 JSON 对象"
    assert set(payload.keys()) == EXPECTED_KEYS, "JSON 键必须且只包含 orbital_period_days 与 reference_mid_transit_time_bkjd"


def test_output_types_and_rounding():
    payload = load_output()
    for key in EXPECTED_KEYS:
        value = payload[key]
        assert isinstance(value, (int, float)), f"{key} 必须是数值类型"
        assert abs(value - round(value, 5)) < 1e-10, f"{key} 必须四舍五入到 5 位小数"


def test_period_value():
    payload = load_output()
    period = float(payload["orbital_period_days"])
    assert abs(period - EXPECTED_PERIOD) <= PERIOD_TOLERANCE, "轨道周期不在允许误差范围内"


def test_epoch_value():
    payload = load_output()
    epoch = float(payload["reference_mid_transit_time_bkjd"])
    assert abs(epoch - EXPECTED_EPOCH) <= EPOCH_TOLERANCE, "参考凌星历元不在允许误差范围内"


def test_epoch_is_in_observed_window():
    payload = load_output()
    epoch = float(payload["reference_mid_transit_time_bkjd"])
    assert 2200.0 <= epoch <= 2266.9, "参考历元必须落在观测时间范围内"
