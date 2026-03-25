from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

import numpy as np

INPUT_PATHS = [
    Path("/root/data/wearable_skin_temp.csv"),
    Path(__file__).resolve().parents[1] / "environment" / "data" / "wearable_skin_temp.csv",
]
MIN_PERIOD = 8.0
MAX_PERIOD = 30.0
GRID_SIZE = 70000
SELECTED_RANGE = (18.0, 30.0)
HARMONIC_RANGE = (10.5, 13.5)
VALUE_TOLERANCE = 0.15


def input_path() -> Path:
    for path in INPUT_PATHS:
        try:
            exists = path.exists()
        except PermissionError:
            exists = False
        if exists:
            return path
    raise AssertionError("Missing wearable skin-temperature input file")


def output_path() -> Path:
    path = Path("/root/circadian_note.md")
    try:
        exists = path.exists()
    except PermissionError:
        exists = False
    if exists:
        return path
    raise AssertionError("Missing /root/circadian_note.md")


def note_lines() -> list[str]:
    return [line.strip() for line in output_path().read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_note() -> tuple[float, float, str]:
    lines = note_lines()
    assert len(lines) == 4, f"Expected exactly 4 non-empty lines, got {len(lines)}"
    assert lines[0] == "# Circadian Rhythm Estimate", f"Unexpected heading: {lines[0]!r}"

    selected_match = re.fullmatch(r"selected_period_hours: (\d+\.\d{2})", lines[1])
    harmonic_match = re.fullmatch(r"harmonic_period_hours: (\d+\.\d{2})", lines[2])
    reason_match = re.fullmatch(r"reason: (.+)", lines[3])

    assert selected_match is not None, f"Invalid selected_period_hours line: {lines[1]!r}"
    assert harmonic_match is not None, f"Invalid harmonic_period_hours line: {lines[2]!r}"
    assert reason_match is not None, f"Invalid reason line: {lines[3]!r}"

    return float(selected_match.group(1)), float(harmonic_match.group(1)), reason_match.group(1)


def load_series() -> tuple[np.ndarray, np.ndarray]:
    times = []
    values = []
    reference_time = None

    with input_path().open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["wear_state"] != "on_wrist":
                continue
            if float(row["quality_score"]) < 0.82:
                continue

            timestamp = datetime.fromisoformat(row["recorded_at"])
            if reference_time is None:
                reference_time = timestamp

            elapsed_hours = (timestamp - reference_time).total_seconds() / 3600.0
            times.append(elapsed_hours)
            values.append(float(row["skin_temp_c"]))

    return np.asarray(times, dtype=float), np.asarray(values, dtype=float)


def compute_expected_periods() -> tuple[float, float]:
    times, values = load_series()
    periods = np.linspace(MIN_PERIOD, MAX_PERIOD, GRID_SIZE)
    centered = values - values.mean()
    rss0 = float(np.sum(np.square(centered)))
    powers = np.empty_like(periods)

    for index, period in enumerate(periods):
        omega = 2.0 * np.pi / period
        design = np.column_stack(
            [
                np.sin(omega * times),
                np.cos(omega * times),
                np.ones_like(times),
            ]
        )
        coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
        residual = values - design @ coefficients
        rss = float(np.sum(np.square(residual)))
        powers[index] = 1.0 - rss / rss0

    peak_mask = (powers[1:-1] > powers[:-2]) & (powers[1:-1] > powers[2:])
    peak_indices = np.flatnonzero(peak_mask) + 1

    selected_candidates = [index for index in peak_indices if SELECTED_RANGE[0] <= periods[index] <= SELECTED_RANGE[1]]
    harmonic_candidates = [index for index in peak_indices if HARMONIC_RANGE[0] <= periods[index] <= HARMONIC_RANGE[1]]

    assert selected_candidates, "Expected at least one circadian-range peak"
    assert harmonic_candidates, "Expected at least one near-12-hour peak"

    selected_index = max(selected_candidates, key=lambda index: powers[index])
    harmonic_index = max(harmonic_candidates, key=lambda index: powers[index])
    return float(periods[selected_index]), float(periods[harmonic_index])


def test_output_exists():
    output_path()


def test_note_shape_and_format():
    selected_period, harmonic_period, _ = parse_note()
    assert SELECTED_RANGE[0] <= selected_period <= SELECTED_RANGE[1], "selected_period_hours is outside 18-30 h"
    assert HARMONIC_RANGE[0] <= harmonic_period <= HARMONIC_RANGE[1], "harmonic_period_hours is outside 10.5-13.5 h"


def test_reported_periods_match_expected_peaks():
    expected_selected, expected_harmonic = compute_expected_periods()
    observed_selected, observed_harmonic, _ = parse_note()

    assert abs(observed_selected - expected_selected) <= VALUE_TOLERANCE, (
        f"Expected selected period near {expected_selected:.2f} h, got {observed_selected:.2f} h"
    )
    assert abs(observed_harmonic - expected_harmonic) <= VALUE_TOLERANCE, (
        f"Expected harmonic period near {expected_harmonic:.2f} h, got {observed_harmonic:.2f} h"
    )


def test_reason_mentions_weaker_harmonic_rejection():
    _, _, reason = parse_note()
    lowered = reason.lower()
    assert "weaker" in lowered, "Reason must say the near-12-hour candidate is weaker"
    assert "harmonic" in lowered, "Reason must explicitly reject the near-12-hour candidate as a harmonic"
