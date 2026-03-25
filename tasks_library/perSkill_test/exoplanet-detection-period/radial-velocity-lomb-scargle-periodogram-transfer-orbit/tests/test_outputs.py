import json
from pathlib import Path

import numpy as np

INPUT_PATH = Path("/root/data/rv_visits.csv")
OUTPUT_PATHS = [Path("/root/rv_period_report.json"), Path("rv_period_report.json")]
MIN_PERIOD = 0.6
MAX_PERIOD = 8.0
MIN_SEPARATION = 0.2
TOLERANCE = 0.05


def output_path() -> Path:
    for path in OUTPUT_PATHS:
        if path.exists():
            return path
    raise AssertionError("Missing /root/rv_period_report.json")


def read_report_text() -> str:
    return output_path().read_text(encoding="utf-8").strip()


def read_report() -> dict:
    return json.loads(read_report_text())


def compute_expected_periods() -> list[float]:
    data = np.genfromtxt(INPUT_PATH, delimiter=",", names=True, dtype=None, encoding="utf-8")
    keep = data["status"] == "keep"

    time = data["bjd_day"][keep]
    velocity = data["rv_mps"][keep] - data["template_drift_mps"][keep]
    error = data["rv_err_mps"][keep]
    weights = 1.0 / np.square(error)

    periods = np.linspace(MIN_PERIOD, MAX_PERIOD, 60000)
    baseline = np.sum(weights * np.square(velocity - np.average(velocity, weights=weights)))
    power = np.empty_like(periods)
    sqrt_weights = np.sqrt(weights)

    for index, period in enumerate(periods):
        omega = 2.0 * np.pi / period
        design = np.column_stack(
            [
                np.sin(omega * time),
                np.cos(omega * time),
                np.ones_like(time),
            ]
        )
        coefficients, *_ = np.linalg.lstsq(design * sqrt_weights[:, None], velocity * sqrt_weights, rcond=None)
        model = design @ coefficients
        residual = velocity - model
        chi_squared = np.sum(weights * np.square(residual))
        power[index] = 1.0 - chi_squared / baseline

    peak_mask = (power[1:-1] > power[:-2]) & (power[1:-1] > power[2:])
    peak_indices = np.flatnonzero(peak_mask) + 1

    ranked = []
    for peak_index in sorted(peak_indices, key=lambda idx: power[idx], reverse=True):
        candidate = float(periods[peak_index])
        if all(abs(candidate - existing) >= MIN_SEPARATION for existing in ranked):
            ranked.append(candidate)
        if len(ranked) == 3:
            break
    return ranked


def is_rounded_to_5_decimals(value: float) -> bool:
    return abs(value - round(value, 5)) < 1e-12


def test_output_exists():
    output_path()


def test_report_shape():
    report = read_report()
    assert isinstance(report, dict), f"Expected a JSON object, got {type(report).__name__}"
    assert set(report) == {"primary_period_days", "alternate_periods_days"}, (
        "Expected exactly the keys primary_period_days and alternate_periods_days"
    )
    assert isinstance(report["alternate_periods_days"], list), "alternate_periods_days must be a JSON array"
    assert len(report["alternate_periods_days"]) == 2, "alternate_periods_days must contain exactly two values"


def test_report_values_are_positive_numbers():
    report = read_report()
    periods = [report["primary_period_days"], *report["alternate_periods_days"]]
    for value in periods:
        assert isinstance(value, (int, float)), f"Expected JSON numbers, got {value!r}"
        assert value > 0.0, f"Periods must be positive, got {value}"
        assert is_rounded_to_5_decimals(float(value)), f"Period {value} is not rounded to 5 decimals"


def test_reported_periods_are_distinct():
    report = read_report()
    periods = [float(report["primary_period_days"]), *map(float, report["alternate_periods_days"])]
    for i, left in enumerate(periods):
        for right in periods[i + 1 :]:
            assert abs(left - right) >= MIN_SEPARATION, (
                f"Periods {left} and {right} are too close; expected at least {MIN_SEPARATION} day separation"
            )


def test_report_matches_expected_ranking():
    expected = compute_expected_periods()
    report = read_report()
    actual = [float(report["primary_period_days"]), *map(float, report["alternate_periods_days"])]

    for observed, target in zip(actual, expected):
        assert abs(observed - target) <= TOLERANCE, (
            f"Expected a reported period near {target:.5f} days, got {observed:.5f}"
        )
