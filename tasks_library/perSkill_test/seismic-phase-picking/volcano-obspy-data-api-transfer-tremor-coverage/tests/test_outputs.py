import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


OUTPUT_FILE = Path("/root/volcano_gap_report.json")
EXPECTED_TOP_LEVEL = {
    "audit_window_start": "2024-07-15T00:00:00.000000Z",
    "audit_window_end": "2024-07-16T00:00:00.000000Z",
    "station_count": 3,
}
EXPECTED_STATIONS = [
    {
        "network": "VG",
        "station": "ACR",
        "location": "",
        "station_name": "Ash Crater Rim",
        "volcano_name": "Mount Kalama",
        "expected_channels": ["DPE", "DPN", "DPZ"],
        "merged_channel_interval_counts": {"DPE": 5, "DPN": 5, "DPZ": 5},
        "coverage_interval_count": 5,
        "coverage_intervals": [
            {
                "start": "2024-07-15T00:00:00.000000Z",
                "end": "2024-07-15T01:20:00.000000Z",
                "duration_sec": 4800.0,
            },
            {
                "start": "2024-07-15T01:30:00.000000Z",
                "end": "2024-07-15T02:00:00.000000Z",
                "duration_sec": 1800.0,
            },
            {
                "start": "2024-07-15T05:00:00.000000Z",
                "end": "2024-07-15T05:45:00.000000Z",
                "duration_sec": 2700.0,
            },
            {
                "start": "2024-07-15T12:10:00.000000Z",
                "end": "2024-07-15T13:00:00.000000Z",
                "duration_sec": 3000.0,
            },
            {
                "start": "2024-07-15T23:20:00.000000Z",
                "end": "2024-07-16T00:00:00.000000Z",
                "duration_sec": 2400.0,
            },
        ],
        "hourly_coverage_seconds": [
            3600.0,
            3000.0,
            0.0,
            0.0,
            0.0,
            2700.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            3000.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            2400.0,
        ],
        "total_covered_seconds": 14700.0,
        "first_missing_interval": {
            "start": "2024-07-15T01:20:00.000000Z",
            "end": "2024-07-15T01:30:00.000000Z",
            "duration_sec": 600.0,
        },
    },
    {
        "network": "VG",
        "station": "BRP",
        "location": "",
        "station_name": "Basalt Rim Pit",
        "volcano_name": "Mount Kalama",
        "expected_channels": ["DPE", "DPN", "DPZ"],
        "merged_channel_interval_counts": {"DPE": 4, "DPN": 4, "DPZ": 4},
        "coverage_interval_count": 4,
        "coverage_intervals": [
            {
                "start": "2024-07-15T00:15:00.000000Z",
                "end": "2024-07-15T00:45:00.000000Z",
                "duration_sec": 1800.0,
            },
            {
                "start": "2024-07-15T08:00:00.000000Z",
                "end": "2024-07-15T10:00:00.000000Z",
                "duration_sec": 7200.0,
            },
            {
                "start": "2024-07-15T10:05:00.000000Z",
                "end": "2024-07-15T10:55:00.000000Z",
                "duration_sec": 3000.0,
            },
            {
                "start": "2024-07-15T18:30:00.000000Z",
                "end": "2024-07-15T19:15:00.000000Z",
                "duration_sec": 2700.0,
            },
        ],
        "hourly_coverage_seconds": [
            1800.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            3600.0,
            3600.0,
            3000.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1800.0,
            900.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ],
        "total_covered_seconds": 14700.0,
        "first_missing_interval": {
            "start": "2024-07-15T00:00:00.000000Z",
            "end": "2024-07-15T00:15:00.000000Z",
            "duration_sec": 900.0,
        },
    },
    {
        "network": "VG",
        "station": "NEG",
        "location": "",
        "station_name": "North Edge Gully",
        "volcano_name": "Mount Kalama",
        "expected_channels": ["DPE", "DPN", "DPZ"],
        "merged_channel_interval_counts": {"DPE": 5, "DPN": 5, "DPZ": 5},
        "coverage_interval_count": 5,
        "coverage_intervals": [
            {
                "start": "2024-07-15T00:00:00.000000Z",
                "end": "2024-07-15T03:00:00.000000Z",
                "duration_sec": 10800.0,
            },
            {
                "start": "2024-07-15T03:10:00.000000Z",
                "end": "2024-07-15T03:40:00.000000Z",
                "duration_sec": 1800.0,
            },
            {
                "start": "2024-07-15T14:00:00.000000Z",
                "end": "2024-07-15T14:50:00.000000Z",
                "duration_sec": 3000.0,
            },
            {
                "start": "2024-07-15T14:55:00.000000Z",
                "end": "2024-07-15T15:30:00.000000Z",
                "duration_sec": 2100.0,
            },
            {
                "start": "2024-07-15T21:00:00.000000Z",
                "end": "2024-07-15T22:00:00.000000Z",
                "duration_sec": 3600.0,
            },
        ],
        "hourly_coverage_seconds": [
            3600.0,
            3600.0,
            3600.0,
            1800.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            3300.0,
            1800.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            3600.0,
            0.0,
            0.0,
        ],
        "total_covered_seconds": 21300.0,
        "first_missing_interval": {
            "start": "2024-07-15T03:00:00.000000Z",
            "end": "2024-07-15T03:10:00.000000Z",
            "duration_sec": 600.0,
        },
    },
]


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@pytest.fixture(scope="module")
def report():
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Missing output file: {OUTPUT_FILE}")
    with OUTPUT_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_top_level(report):
    for key, expected in EXPECTED_TOP_LEVEL.items():
        assert report.get(key) == expected
    assert list(report.keys()) == [
        "audit_window_start",
        "audit_window_end",
        "station_count",
        "stations",
    ]


@pytest.mark.parametrize("index", range(len(EXPECTED_STATIONS)))
def test_station_payload(index, report):
    actual = report["stations"][index]
    expected = EXPECTED_STATIONS[index]

    for key in [
        "network",
        "station",
        "location",
        "station_name",
        "volcano_name",
        "expected_channels",
        "merged_channel_interval_counts",
        "coverage_interval_count",
    ]:
        assert actual[key] == expected[key]

    assert len(actual["coverage_intervals"]) == len(expected["coverage_intervals"])
    for actual_interval, expected_interval in zip(actual["coverage_intervals"], expected["coverage_intervals"]):
        assert parse_time(actual_interval["start"]) == parse_time(expected_interval["start"])
        assert parse_time(actual_interval["end"]) == parse_time(expected_interval["end"])
        assert float(actual_interval["duration_sec"]) == pytest.approx(expected_interval["duration_sec"], abs=1e-6)

    assert actual["hourly_coverage_seconds"] == pytest.approx(expected["hourly_coverage_seconds"], abs=1e-6)
    assert float(actual["total_covered_seconds"]) == pytest.approx(expected["total_covered_seconds"], abs=1e-6)

    actual_gap = actual["first_missing_interval"]
    expected_gap = expected["first_missing_interval"]
    assert parse_time(actual_gap["start"]) == parse_time(expected_gap["start"])
    assert parse_time(actual_gap["end"]) == parse_time(expected_gap["end"])
    assert float(actual_gap["duration_sec"]) == pytest.approx(expected_gap["duration_sec"], abs=1e-6)


def test_decoy_inputs_do_not_leak(report):
    stations = {(item["network"], item["station"], item["location"]) for item in report["stations"]}
    assert ("VG", "XTR", "") not in stations

    brp = next(item for item in report["stations"] if item["station"] == "BRP")
    assert brp["hourly_coverage_seconds"][10] == pytest.approx(3000.0, abs=1e-6)
    assert brp["hourly_coverage_seconds"][11] == pytest.approx(0.0, abs=1e-6)
