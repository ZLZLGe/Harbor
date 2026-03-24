import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest


OUTPUT_FILE = Path("/root/arrival_windows.csv")
EXPECTED_COLUMNS = [
    "event_id",
    "network",
    "station",
    "location",
    "waveform_file",
    "origin_time",
    "trace_start",
    "trace_end",
    "review_start",
    "review_end",
    "start_offset_sec",
    "end_offset_sec",
    "sample_rate_hz",
    "window_duration_sec",
    "channel_count",
    "channel_coverage",
]
EXPECTED_ROWS = [
    {
        "event_id": "aft_001",
        "network": "BK",
        "station": "BRIB",
        "location": "",
        "waveform_file": "aft001_bk_brib_bundle.npz",
        "origin_time": "2024-04-17T03:22:10.000000Z",
        "trace_start": "2024-04-17T03:22:02.000000Z",
        "trace_end": "2024-04-17T03:22:38.000000Z",
        "review_start": "2024-04-17T03:22:05.000000Z",
        "review_end": "2024-04-17T03:22:35.000000Z",
        "start_offset_sec": -5.0,
        "end_offset_sec": 25.0,
        "sample_rate_hz": 100.0,
        "window_duration_sec": 30.0,
        "channel_count": 3,
        "channel_coverage": "HHE|HHN|HHZ",
    },
    {
        "event_id": "aft_001",
        "network": "CI",
        "station": "PLM",
        "location": "",
        "waveform_file": "aft001_ci_plm_bundle.json",
        "origin_time": "2024-04-17T03:22:10.000000Z",
        "trace_start": "2024-04-17T03:22:08.000000Z",
        "trace_end": "2024-04-17T03:22:36.000000Z",
        "review_start": "2024-04-17T03:22:08.000000Z",
        "review_end": "2024-04-17T03:22:35.000000Z",
        "start_offset_sec": -2.0,
        "end_offset_sec": 25.0,
        "sample_rate_hz": 50.0,
        "window_duration_sec": 27.0,
        "channel_count": 3,
        "channel_coverage": "BHE|BHN|BHZ",
    },
    {
        "event_id": "aft_002",
        "network": "NC",
        "station": "GDXB",
        "location": "",
        "waveform_file": "aft002_nc_gdxb_bundle.json",
        "origin_time": "2024-04-18T11:04:30.500000Z",
        "trace_start": "2024-04-18T11:04:32.000000Z",
        "trace_end": "2024-04-18T11:04:56.000000Z",
        "review_start": "2024-04-18T11:04:32.000000Z",
        "review_end": "2024-04-18T11:04:50.500000Z",
        "start_offset_sec": 1.5,
        "end_offset_sec": 20.0,
        "sample_rate_hz": 100.0,
        "window_duration_sec": 18.5,
        "channel_count": 3,
        "channel_coverage": "HNE|HNN|HNZ",
    },
    {
        "event_id": "aft_002",
        "network": "PG",
        "station": "LM",
        "location": "",
        "waveform_file": "aft002_pg_lm_two_component.npz",
        "origin_time": "2024-04-18T11:04:30.500000Z",
        "trace_start": "2024-04-18T11:04:21.500000Z",
        "trace_end": "2024-04-18T11:05:09.500000Z",
        "review_start": "2024-04-18T11:04:22.500000Z",
        "review_end": "2024-04-18T11:04:50.500000Z",
        "start_offset_sec": -8.0,
        "end_offset_sec": 20.0,
        "sample_rate_hz": 25.0,
        "window_duration_sec": 28.0,
        "channel_count": 2,
        "channel_coverage": "EHE|EHN",
    },
    {
        "event_id": "aft_003",
        "network": "BK",
        "station": "MHC",
        "location": "00",
        "waveform_file": "aft003_bk_mhc_review.csv",
        "origin_time": "2024-04-19T22:41:05.250000Z",
        "trace_start": "2024-04-19T22:41:01.250000Z",
        "trace_end": "2024-04-19T22:41:28.250000Z",
        "review_start": "2024-04-19T22:41:01.250000Z",
        "review_end": "2024-04-19T22:41:23.250000Z",
        "start_offset_sec": -4.0,
        "end_offset_sec": 18.0,
        "sample_rate_hz": 20.0,
        "window_duration_sec": 22.0,
        "channel_count": 3,
        "channel_coverage": "BHE|BHN|BHZ",
    },
]


def parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_rows():
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Missing output file: {OUTPUT_FILE}")

    with OUTPUT_FILE.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        header = reader.fieldnames

    return header, rows


def test_header_and_row_count():
    header, rows = load_rows()
    assert header == EXPECTED_COLUMNS
    assert len(rows) == len(EXPECTED_ROWS)


@pytest.mark.parametrize("index", range(len(EXPECTED_ROWS)))
def test_expected_rows(index):
    _, rows = load_rows()
    actual = rows[index]
    expected = EXPECTED_ROWS[index]

    for key in ["event_id", "network", "station", "location", "waveform_file", "channel_coverage"]:
        assert actual[key] == expected[key]

    for key in ["origin_time", "trace_start", "trace_end", "review_start", "review_end"]:
        assert parse_iso8601(actual[key]) == parse_iso8601(expected[key])

    for key in ["start_offset_sec", "end_offset_sec", "sample_rate_hz", "window_duration_sec"]:
        assert float(actual[key]) == pytest.approx(expected[key], abs=1e-6)

    assert int(actual["channel_count"]) == expected["channel_count"]


def test_unusable_waveforms_are_excluded():
    _, rows = load_rows()
    waveform_names = {row["waveform_file"] for row in rows}
    assert "aft001_nn_lhv_single.csv" not in waveform_names
    assert "aft003_ta_p01c_late_start.npz" not in waveform_names
