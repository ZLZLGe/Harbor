import csv
from datetime import datetime
from pathlib import Path

from obspy import Stream, UTCDateTime, read


OUTPUT_PATH = Path("/root/shot_window_summary.csv")
WAVEFORM_PATH = "/root/data/survey_line_12_continuous.mseed"
ROSTER_PATH = "/root/data/receiver_roster.csv"
SCHEDULE_PATH = "/root/data/shot_schedule.csv"
PRE_WINDOW_SECONDS = 3.0
POST_WINDOW_SECONDS = 7.0
EXPECTED_COLUMNS = [
    "shot_id",
    "line_name",
    "shot_time",
    "window_start",
    "window_end",
    "trace_count",
    "station_count",
    "sample_rates_hz",
    "total_samples",
]


def format_time(value: UTCDateTime) -> str:
    return value.datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")


def trace_key(trace) -> tuple[str, str, str, str]:
    return (
        trace.stats.network,
        trace.stats.station,
        trace.stats.location,
        trace.stats.channel,
    )


def load_output_rows():
    assert OUTPUT_PATH.exists(), "missing /root/shot_window_summary.csv"
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_allowed_receivers() -> set[tuple[str, str, str, str]]:
    allowed = set()
    with open(ROSTER_PATH, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["enabled"] == "1":
                allowed.add((row["network"], row["station"], row["location"], row["channel"]))
    return allowed


def format_sample_rates(traces) -> str:
    if not traces:
        return ""
    rates = sorted({float(trace.stats.sampling_rate) for trace in traces})
    return "|".join(f"{rate:.1f}" for rate in rates)


def build_expected_rows():
    allowed = load_allowed_receivers()
    stream = read(WAVEFORM_PATH)
    filtered = Stream(traces=[trace for trace in stream if trace_key(trace) in allowed])

    rows = []
    with open(SCHEDULE_PATH, newline="", encoding="utf-8") as handle:
        for shot in csv.DictReader(handle):
            shot_time = UTCDateTime(shot["shot_time"])
            window_start = shot_time - PRE_WINDOW_SECONDS
            window_end = shot_time + POST_WINDOW_SECONDS
            windowed = filtered.copy().slice(starttime=window_start, endtime=window_end)
            counted = [trace for trace in windowed if trace.stats.npts > 0]
            rows.append(
                {
                    "shot_id": shot["shot_id"],
                    "line_name": shot["line_name"],
                    "shot_time": format_time(shot_time),
                    "window_start": format_time(window_start),
                    "window_end": format_time(window_end),
                    "trace_count": len(counted),
                    "station_count": len({trace.stats.station for trace in counted}),
                    "sample_rates_hz": format_sample_rates(counted),
                    "total_samples": sum(trace.stats.npts for trace in counted),
                }
            )

    return sorted(rows, key=lambda row: (row["shot_time"], row["shot_id"]))


def test_output_contract_and_values():
    actual_rows = load_output_rows()
    expected_rows = build_expected_rows()

    assert actual_rows, "output CSV must not be empty"
    assert list(actual_rows[0].keys()) == EXPECTED_COLUMNS, "output columns do not match the instruction"
    assert len(actual_rows) == len(expected_rows), "every scheduled shot must appear exactly once"

    actual_order = [(row["shot_time"], row["shot_id"]) for row in actual_rows]
    expected_order = [(row["shot_time"], row["shot_id"]) for row in expected_rows]
    assert actual_order == expected_order, "rows must be sorted by shot_time ascending and tie-broken by shot_id"

    for actual, expected in zip(actual_rows, expected_rows, strict=True):
        assert actual["shot_id"] == expected["shot_id"]
        assert actual["line_name"] == expected["line_name"]
        assert actual["shot_time"] == expected["shot_time"]
        assert actual["window_start"] == expected["window_start"]
        assert actual["window_end"] == expected["window_end"]
        assert int(actual["trace_count"]) == expected["trace_count"]
        assert int(actual["station_count"]) == expected["station_count"]
        assert actual["sample_rates_hz"] == expected["sample_rates_hz"]
        assert int(actual["total_samples"]) == expected["total_samples"]

        parsed_shot = datetime.fromisoformat(actual["shot_time"])
        parsed_start = datetime.fromisoformat(actual["window_start"])
        parsed_end = datetime.fromisoformat(actual["window_end"])
        assert parsed_shot.tzinfo is None
        assert parsed_start.tzinfo is None
        assert parsed_end.tzinfo is None
        assert (parsed_shot - parsed_start).total_seconds() == PRE_WINDOW_SECONDS
        assert (parsed_end - parsed_shot).total_seconds() == POST_WINDOW_SECONDS


def test_dataset_requires_sorting_and_zero_hit_handling():
    expected_rows = build_expected_rows()

    with open(SCHEDULE_PATH, newline="", encoding="utf-8") as handle:
        input_rows = list(csv.DictReader(handle))

    input_order = [(row["shot_time"], row["shot_id"]) for row in input_rows]
    sorted_order = sorted(input_order)
    assert input_order != sorted_order, "task data should require explicit output sorting"

    trace_counts = [row["trace_count"] for row in expected_rows]
    assert any(count == 0 for count in trace_counts), "task data should include at least one zero-hit shot"
    assert any(count > 0 for count in trace_counts), "task data should include at least one shot with waveform hits"
    assert any(row["trace_count"] > row["station_count"] for row in expected_rows), "task data should include multi-channel station hits"
