import json
import math
from pathlib import Path

import pandas as pd


OUTPUT_PATH = Path("/root/observable_transits.json")
LIGHTCURVE_PATH = Path("/root/data/followup_lightcurve.csv")
WINDOWS_PATH = Path("/root/data/visibility_windows.json")

EXPECTED_PERIOD = 7.28465
EXPECTED_T0 = 2461003.48210
EXPECTED_EVENTS = [
    ("WIN-02", 8, 2461061.75930),
    ("WIN-04", 10, 2461076.32860),
    ("WIN-06", 12, 2461090.89790),
]

PERIOD_TOLERANCE = 0.01
T0_TOLERANCE = 0.05
MIDPOINT_TOLERANCE = 0.08


def load_output():
    assert OUTPUT_PATH.exists(), "Expected output file /root/observable_transits.json was not created."
    with OUTPUT_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_windows():
    with WINDOWS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def compute_observable_from_report(period_days, t0_bjd, windows):
    earliest = min(window["start_bjd"] for window in windows)
    latest = max(window["end_bjd"] for window in windows)
    start_cycle = max(0, math.ceil((earliest - t0_bjd) / period_days))
    end_cycle = math.floor((latest - t0_bjd) / period_days)

    events = []
    for cycle in range(start_cycle, end_cycle + 1):
        midpoint = round(t0_bjd + cycle * period_days, 5)
        for window in windows:
            if window["start_bjd"] <= midpoint <= window["end_bjd"]:
                events.append((window["window_id"], cycle, midpoint))
                break
    return events


def test_output_object_and_keys():
    payload = load_output()
    assert isinstance(payload, dict), "observable_transits.json must contain a JSON object."
    assert set(payload.keys()) == {"period_days", "t0_bjd", "observable_transits"}, (
        "The output JSON must contain exactly 'period_days', 't0_bjd', and 'observable_transits'."
    )


def test_ephemeris_is_numeric_positive_and_rounded():
    payload = load_output()
    period = payload["period_days"]
    t0 = payload["t0_bjd"]

    assert isinstance(period, (int, float)), "period_days must be a JSON number."
    assert isinstance(t0, (int, float)), "t0_bjd must be a JSON number."
    assert float(period) > 0, "period_days must be positive."
    assert round(float(period), 5) == float(period), "period_days must be rounded to 5 decimal places."
    assert round(float(t0), 5) == float(t0), "t0_bjd must be rounded to 5 decimal places."


def test_ephemeris_matches_dataset_solution():
    payload = load_output()
    period = float(payload["period_days"])
    t0 = float(payload["t0_bjd"])

    assert abs(period - EXPECTED_PERIOD) <= PERIOD_TOLERANCE, (
        f"Recovered period {period:.5f} is too far from the dataset solution {EXPECTED_PERIOD:.5f}."
    )
    assert abs(t0 - EXPECTED_T0) <= T0_TOLERANCE, (
        f"Recovered t0 {t0:.5f} is too far from the dataset solution {EXPECTED_T0:.5f}."
    )


def test_t0_is_first_in_range_mid_transit():
    payload = load_output()
    period = float(payload["period_days"])
    t0 = float(payload["t0_bjd"])

    frame = pd.read_csv(LIGHTCURVE_PATH)
    good = frame.loc[frame["quality"] == 0]
    time_min = float(good["time_bjd"].min())
    time_max = float(good["time_bjd"].max())

    assert time_min <= t0 <= time_max, "t0_bjd must lie within the retained quality==0 time range."
    assert t0 - period < time_min, "t0_bjd must be the first modeled mid-transit inside the retained time range."
    assert t0 <= time_max, "t0_bjd must not lie after the observed time range."


def test_observable_transits_have_required_structure():
    payload = load_output()
    events = payload["observable_transits"]

    assert isinstance(events, list), "observable_transits must be a JSON array."
    assert len(events) == len(EXPECTED_EVENTS), "The dataset has exactly three observable future transits."

    midpoints = []
    for event in events:
        assert isinstance(event, dict), "Each observable transit must be a JSON object."
        assert set(event.keys()) == {"window_id", "transit_number", "mid_transit_bjd"}, (
            "Each observable transit must contain exactly 'window_id', 'transit_number', and 'mid_transit_bjd'."
        )
        assert isinstance(event["window_id"], str) and event["window_id"], "window_id must be a non-empty string."
        assert isinstance(event["transit_number"], int), "transit_number must be an integer."
        assert event["transit_number"] >= 0, "transit_number must be non-negative."
        midpoint = float(event["mid_transit_bjd"])
        assert round(midpoint, 5) == midpoint, "mid_transit_bjd must be rounded to 5 decimal places."
        midpoints.append(midpoint)

    assert midpoints == sorted(midpoints), "observable_transits must be sorted by ascending mid_transit_bjd."


def test_observable_transits_match_windows_and_reported_ephemeris():
    payload = load_output()
    period = float(payload["period_days"])
    t0 = float(payload["t0_bjd"])
    events = payload["observable_transits"]
    windows = load_windows()
    window_lookup = {window["window_id"]: window for window in windows}

    computed = compute_observable_from_report(period, t0, windows)
    observed = [(event["window_id"], event["transit_number"], float(event["mid_transit_bjd"])) for event in events]
    assert observed == computed, (
        "observable_transits must equal the set of predicted mid-transits between the earliest and latest "
        "window bounds that fall inside a listed visibility window."
    )

    for event in events:
        midpoint = float(event["mid_transit_bjd"])
        cycle = int(event["transit_number"])
        expected_midpoint = round(t0 + cycle * period, 5)
        assert midpoint == expected_midpoint, (
            "Each mid_transit_bjd must be consistent with the reported period_days, t0_bjd, and transit_number."
        )
        window = window_lookup[event["window_id"]]
        assert window["start_bjd"] <= midpoint <= window["end_bjd"], (
            f"mid_transit_bjd {midpoint:.5f} must lie inside the matching visibility window."
        )


def test_observable_transits_match_dataset_sequence():
    payload = load_output()
    events = payload["observable_transits"]

    assert [event["window_id"] for event in events] == [item[0] for item in EXPECTED_EVENTS]
    assert [event["transit_number"] for event in events] == [item[1] for item in EXPECTED_EVENTS]

    for event, (_, _, expected_midpoint) in zip(events, EXPECTED_EVENTS):
        midpoint = float(event["mid_transit_bjd"])
        assert abs(midpoint - expected_midpoint) <= MIDPOINT_TOLERANCE, (
            f"Predicted midpoint {midpoint:.5f} is too far from the dataset solution {expected_midpoint:.5f}."
        )
