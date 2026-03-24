import csv
import os
from pathlib import Path

import numpy as np
import pytest


def get_repo_root():
    return Path(__file__).resolve().parents[1]


def get_input_path():
    root_path = Path("/root/data/asteroid_ground_photometry.csv")
    if root_path.exists():
        return root_path
    return get_repo_root() / "environment" / "data" / "asteroid_ground_photometry.csv"


def get_output_path():
    for candidate in (Path("/root/asteroid_cleaned.csv"), Path("asteroid_cleaned.csv")):
        if candidate.exists():
            return candidate
    return None


def running_median(values, window):
    half_window = window // 2
    med = np.empty_like(values)
    for idx in range(len(values)):
        lo = max(0, idx - half_window)
        hi = min(len(values), idx + half_window + 1)
        med[idx] = np.median(values[lo:hi])
    return med


def compute_expected_series():
    data = np.genfromtxt(get_input_path(), delimiter=",", names=True, dtype=None, encoding="utf-8")

    time = data["time_jd"].astype(float)
    flux = data["diff_flux"].astype(float)
    night_id = data["night_id"].astype(int)
    quality_flag = data["quality_flag"].astype(int)

    keep = quality_flag == 0
    time = time[keep]
    flux = flux[keep]
    night_id = night_id[keep]

    all_times = []
    all_fluxes = []

    for night in np.unique(night_id):
        night_mask = night_id == night
        night_time = time[night_mask]
        night_flux = flux[night_mask]

        local_median = running_median(night_flux, 21)
        residual = night_flux - local_median
        residual_center = np.median(residual)
        sigma = 1.4826 * np.median(np.abs(residual - residual_center))
        keep_night = np.abs(residual - residual_center) <= 5.0 * sigma

        night_time = night_time[keep_night]
        night_flux = night_flux[keep_night]
        night_flux = night_flux / np.median(night_flux)

        x = night_time - np.median(night_time)
        design = np.column_stack([np.ones_like(x), x])
        coeffs, _, _, _ = np.linalg.lstsq(design, night_flux, rcond=None)
        trend = design @ coeffs
        clean_flux = night_flux / trend

        all_times.append(night_time)
        all_fluxes.append(clean_flux)

    expected_time = np.concatenate(all_times)
    expected_flux = np.concatenate(all_fluxes)
    order = np.argsort(expected_time)
    expected_time = expected_time[order]
    expected_flux = expected_flux[order]
    expected_flux = expected_flux / np.median(expected_flux)
    return expected_time, expected_flux


def load_output_series(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames == ["time_jd", "clean_flux"], (
        f"Expected header ['time_jd', 'clean_flux'], got {reader.fieldnames}"
    )

    time = np.array([float(row["time_jd"]) for row in rows], dtype=float)
    flux = np.array([float(row["clean_flux"]) for row in rows], dtype=float)
    return time, flux


class TestAsteroidCleaningTask:
    TIME_TOLERANCE = 5e-8
    MEAN_ABS_TOL = 8e-5
    MAX_ABS_TOL = 5e-4

    def test_output_exists(self):
        assert get_output_path() is not None, "Expected /root/asteroid_cleaned.csv to be created"

    def test_output_has_expected_length_and_order(self):
        output_path = get_output_path()
        if output_path is None:
            pytest.skip("Output missing")

        reported_time, _ = load_output_series(output_path)
        expected_time, _ = compute_expected_series()

        assert len(reported_time) == len(expected_time), (
            f"Expected {len(expected_time)} cleaned rows, got {len(reported_time)}"
        )
        assert np.all(np.diff(reported_time) > 0), "Output timestamps must be strictly increasing"

    def test_timestamps_match_surviving_cadences(self):
        output_path = get_output_path()
        if output_path is None:
            pytest.skip("Output missing")

        reported_time, _ = load_output_series(output_path)
        expected_time, _ = compute_expected_series()
        max_time_error = float(np.max(np.abs(reported_time - expected_time)))
        assert max_time_error <= self.TIME_TOLERANCE, (
            f"Timestamps differ from expected surviving cadences by up to {max_time_error:.2e} days"
        )

    def test_clean_flux_matches_benchmark(self):
        output_path = get_output_path()
        if output_path is None:
            pytest.skip("Output missing")

        _, reported_flux = load_output_series(output_path)
        _, expected_flux = compute_expected_series()

        abs_error = np.abs(reported_flux - expected_flux)
        assert np.median(reported_flux) == pytest.approx(1.0, abs=1e-6)
        assert float(np.mean(abs_error)) <= self.MEAN_ABS_TOL, (
            f"Mean absolute flux error {np.mean(abs_error):.2e} exceeds {self.MEAN_ABS_TOL:.2e}"
        )
        assert float(np.max(abs_error)) <= self.MAX_ABS_TOL, (
            f"Max absolute flux error {np.max(abs_error):.2e} exceeds {self.MAX_ABS_TOL:.2e}"
        )

    def test_flux_range_is_reasonable(self):
        output_path = get_output_path()
        if output_path is None:
            pytest.skip("Output missing")

        _, reported_flux = load_output_series(output_path)
        assert np.all(reported_flux > 0.9), "Cleaned flux should remain positive and near unity"
        assert np.all(reported_flux < 1.1), "Cleaned flux still contains implausibly large excursions"
