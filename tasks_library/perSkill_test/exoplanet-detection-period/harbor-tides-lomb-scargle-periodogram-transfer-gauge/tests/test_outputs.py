from __future__ import annotations

import csv
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

MIN_PERIOD_HOURS = 8.0
MAX_PERIOD_HOURS = 30.0
MIN_SEPARATION_HOURS = 0.35
GRID_SIZE = 70000
PERIOD_TOLERANCE = 0.08
POWER_TOLERANCE = 0.02

OUTPUT_PATHS = [Path("/root/tide_peak_table.csv")]


def ensure_input_path() -> Path:
    direct_candidates = [
        Path("/root/data/harbor_gauge.csv"),
        Path(__file__).resolve().parents[1] / "environment" / "data" / "harbor_gauge.csv",
    ]
    for candidate in direct_candidates:
        try:
            exists = candidate.exists()
        except PermissionError:
            exists = False
        if exists:
            return candidate

    generator = Path(__file__).resolve().parents[1] / "environment" / "scripts" / "generate_harbor_gauge.py"
    local_output = Path(__file__).resolve().parents[1] / "environment" / "data" / "harbor_gauge.csv"
    if generator.exists():
        local_output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([sys.executable, str(generator), str(local_output)])
        return local_output

    raise AssertionError("Missing harbor gauge input file")


def output_path() -> Path:
    for candidate in OUTPUT_PATHS:
        try:
            exists = candidate.exists()
        except PermissionError:
            exists = False
        if exists:
            return candidate
    raise AssertionError("Missing /root/tide_peak_table.csv")


def output_text() -> str:
    return output_path().read_text(encoding="utf-8").strip()


def output_rows() -> list[dict[str, str]]:
    with output_path().open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_series() -> tuple[np.ndarray, np.ndarray]:
    input_path = ensure_input_path()
    times = []
    values = []
    reference_time = None

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["qc_flag"] != "ok":
                continue

            timestamp = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
            if reference_time is None:
                reference_time = timestamp

            delta_hours = (timestamp - reference_time).total_seconds() / 3600.0
            corrected_level = float(row["water_level_m"]) - float(row["sensor_offset_m"])
            times.append(delta_hours)
            values.append(corrected_level)

    return np.asarray(times, dtype=float), np.asarray(values, dtype=float)


def compute_top_peaks() -> list[tuple[float, float]]:
    times, values = load_series()
    periods = np.linspace(MIN_PERIOD_HOURS, MAX_PERIOD_HOURS, GRID_SIZE)
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

    peaks: list[tuple[float, float]] = []
    for peak_index in sorted(peak_indices, key=lambda item: powers[item], reverse=True):
        period = float(periods[peak_index])
        power = float(powers[peak_index])
        if all(abs(period - existing_period) >= MIN_SEPARATION_HOURS for existing_period, _ in peaks):
            peaks.append((period, power))
        if len(peaks) == 3:
            return peaks

    raise AssertionError("Expected three distinct peaks")


def test_output_exists():
    output_path()


def test_csv_header_and_row_count():
    content = output_text().splitlines()
    assert content[0] == "rank,period_hours,power", f"Unexpected header: {content[0]!r}"
    assert len(content) == 4, f"Expected header plus 3 rows, got {len(content)} lines"


def test_csv_shape_and_ranks():
    rows = output_rows()
    assert len(rows) == 3, f"Expected exactly 3 data rows, got {len(rows)}"
    assert rows[0].keys() == {"rank", "period_hours", "power"}
    assert [row["rank"] for row in rows] == ["1", "2", "3"], "Ranks must be 1, 2, 3 in order"


def test_numeric_format_and_ranges():
    rows = output_rows()
    pattern = re.compile(r"^-?\d+\.\d{5}$")
    for row in rows:
        assert pattern.match(row["period_hours"]), f"period_hours must have 5 decimals: {row['period_hours']!r}"
        assert pattern.match(row["power"]), f"power must have 5 decimals: {row['power']!r}"
        period = float(row["period_hours"])
        power = float(row["power"])
        assert MIN_PERIOD_HOURS <= period <= MAX_PERIOD_HOURS, f"Period out of range: {period}"
        assert 0.0 <= power <= 1.0, f"Power must be between 0 and 1, got {power}"


def test_periods_are_distinct_and_sorted_by_power():
    rows = output_rows()
    periods = [float(row["period_hours"]) for row in rows]
    powers = [float(row["power"]) for row in rows]

    assert powers == sorted(powers, reverse=True), "Rows must be ordered from strongest to weakest power"
    for index, left in enumerate(periods):
        for right in periods[index + 1 :]:
            assert abs(left - right) >= MIN_SEPARATION_HOURS, (
                f"Periods {left:.5f} and {right:.5f} are too close"
            )


def test_report_matches_expected_peaks():
    expected = compute_top_peaks()
    rows = output_rows()

    for row, (expected_period, expected_power) in zip(rows, expected):
        observed_period = float(row["period_hours"])
        observed_power = float(row["power"])
        assert abs(observed_period - expected_period) <= PERIOD_TOLERANCE, (
            f"Expected a period near {expected_period:.5f} hours, got {observed_period:.5f}"
        )
        assert abs(observed_power - expected_power) <= POWER_TOLERANCE, (
            f"Expected a power near {expected_power:.5f}, got {observed_power:.5f}"
        )
