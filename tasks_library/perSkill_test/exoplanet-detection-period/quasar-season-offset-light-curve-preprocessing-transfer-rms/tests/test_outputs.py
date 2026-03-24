import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

import pytest


def get_repo_root():
    return Path(__file__).resolve().parents[1]


def get_data_path():
    root_path = Path("/root/data/quasar_monitoring.csv")
    try:
        if root_path.exists():
            return root_path
    except PermissionError:
        pass
    return get_repo_root() / "environment" / "data" / "quasar_monitoring.csv"


def get_output_path():
    for candidate in (Path("/root/quasar_rms.txt"), Path("quasar_rms.txt")):
        try:
            if candidate.exists():
                return candidate
        except PermissionError:
            continue
    return None


def running_median(values, window):
    half_window = window // 2
    medians = []
    for idx in range(len(values)):
        lo = max(0, idx - half_window)
        hi = min(len(values), idx + half_window + 1)
        medians.append(statistics.median(values[lo:hi]))
    return medians


def load_rows():
    with get_data_path().open(newline="") as f:
        return list(csv.DictReader(f))


def compute_expected_rms():
    rows = []
    for row in load_rows():
        if int(row["quality_flag"]) != 0:
            continue
        rows.append(
            {
                "mjd": float(row["mjd"]),
                "relative_flux": float(row["relative_flux"]),
                "season_id": int(row["season_id"]),
            }
        )

    rows.sort(key=lambda row: (row["season_id"], row["mjd"]))
    by_season = defaultdict(list)
    for row in rows:
        by_season[row["season_id"]].append(row)

    residuals = []
    for season_id in sorted(by_season):
        season_rows = by_season[season_id]
        flux = [row["relative_flux"] for row in season_rows]
        local_baseline = running_median(flux, 5)
        local_residual = [value - baseline for value, baseline in zip(flux, local_baseline)]
        center = statistics.median(local_residual)
        sigma = 1.4826 * statistics.median(abs(value - center) for value in local_residual)

        cleaned_rows = [
            row
            for row, value in zip(season_rows, local_residual)
            if abs(value - center) <= 4.5 * sigma
        ]

        cleaned_flux = [row["relative_flux"] for row in cleaned_rows]
        season_median = statistics.median(cleaned_flux)
        normalized_flux = [value / season_median for value in cleaned_flux]
        seasonal_trend = running_median(normalized_flux, 9)
        residuals.extend([value / trend - 1.0 for value, trend in zip(normalized_flux, seasonal_trend)])

    return math.sqrt(sum(value * value for value in residuals) / len(residuals))


def compute_raw_season_scatter():
    rows = []
    for row in load_rows():
        if int(row["quality_flag"]) != 0:
            continue
        rows.append(
            {
                "relative_flux": float(row["relative_flux"]),
                "season_id": int(row["season_id"]),
            }
        )

    by_season = defaultdict(list)
    for row in rows:
        by_season[row["season_id"]].append(row["relative_flux"])

    residuals = []
    for season_id in sorted(by_season):
        season_flux = by_season[season_id]
        season_median = statistics.median(season_flux)
        residuals.extend([value / season_median - 1.0 for value in season_flux])

    return math.sqrt(sum(value * value for value in residuals) / len(residuals))


class TestQuasarResidualRMS:
    TOLERANCE = 5e-6

    def test_output_exists(self):
        assert get_output_path() is not None, "Expected /root/quasar_rms.txt to be created"

    def test_output_is_numeric(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output missing")

        value = float(path.read_text().strip())
        assert 0.0 < value < 0.02, f"Residual RMS should be between 0 and 0.02, got {value}"

    def test_output_matches_benchmark(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output missing")

        reported = float(path.read_text().strip())
        expected = compute_expected_rms()
        assert abs(reported - expected) <= self.TOLERANCE, (
            f"Reported RMS {reported:.6f} differs from benchmark {expected:.6f} "
            f"by more than {self.TOLERANCE:.6f}"
        )

    def test_cleaning_reduces_scatter(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output missing")

        reported = float(path.read_text().strip())
        raw_scatter = compute_raw_season_scatter()
        assert reported < raw_scatter / 2.0, (
            f"Reported RMS {reported:.6f} is not much smaller than raw seasonal scatter {raw_scatter:.6f}"
        )

    def test_output_precision(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output missing")

        text = path.read_text().strip()
        assert "." in text, f"Expected decimal output, got {text}"
        decimals = len(text.split(".")[-1])
        assert decimals <= 6, f"Expected at most 6 decimal places, got {text}"
