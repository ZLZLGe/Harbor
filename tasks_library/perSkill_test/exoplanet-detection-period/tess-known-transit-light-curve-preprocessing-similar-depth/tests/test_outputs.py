import csv
import os
from pathlib import Path

import numpy as np
import pytest


def get_data_path(filename):
    root_path = Path("/root/data") / filename
    try:
        if root_path.exists():
            return root_path
    except PermissionError:
        pass

    repo_path = (
        Path(__file__).resolve().parents[1]
        / "environment"
        / "data"
        / filename
    )
    return repo_path


def get_output_path():
    for path in ("/root/transit_depth.txt", "transit_depth.txt"):
        try:
            if os.path.exists(path):
                return path
        except PermissionError:
            continue
    return None


def load_ephemeris(path):
    with open(path, newline="") as f:
        row = next(csv.DictReader(f))
    return (
        float(row["period_days"]),
        float(row["reference_mid_transit_btjd"]),
        float(row["transit_duration_hours"]) / 24.0,
    )


def compute_benchmark_depth():
    data = np.genfromtxt(get_data_path("known_transit_lc.csv"), delimiter=",", names=True)
    period, t0, duration = load_ephemeris(get_data_path("known_ephemeris.csv"))

    good = data["quality_flag"].astype(int) == 0
    time = data["time_btjd"].astype(float)[good]
    flux = data["normalized_flux"].astype(float)[good]

    median_flux = np.median(flux)
    mad_flux = np.median(np.abs(flux - median_flux))
    sigma_flux = 1.4826 * mad_flux
    keep = np.abs(flux - median_flux) <= 6.0 * sigma_flux
    time = time[keep]
    flux = flux[keep]

    phase = ((time - t0 + 0.5 * period) % period) - 0.5 * period
    trend_mask = np.abs(phase) <= 0.75 * duration
    interp_flux = np.interp(time, time[~trend_mask], flux[~trend_mask])

    window = 301
    kernel = np.ones(window, dtype=float) / window
    pad = window // 2
    trend = np.convolve(np.pad(interp_flux, (pad, pad), mode="edge"), kernel, mode="valid")
    flat_flux = flux / trend

    complete = np.zeros(len(time), dtype=bool)
    n_start = int(np.floor((time.min() - t0) / period)) - 1
    n_stop = int(np.ceil((time.max() - t0) / period)) + 1
    for n in range(n_start, n_stop + 1):
        mid_transit = t0 + n * period
        if mid_transit - 3.0 * duration < time.min():
            continue
        if mid_transit + 3.0 * duration > time.max():
            continue
        complete |= np.abs(time - mid_transit) <= 3.0 * duration

    phase = ((time - t0 + 0.5 * period) % period) - 0.5 * period
    in_transit = complete & (np.abs(phase) <= duration / 2.0)
    baseline = complete & (np.abs(phase) >= duration) & (np.abs(phase) <= 3.0 * duration)
    return float(np.median(flat_flux[baseline]) - np.median(flat_flux[in_transit]))


class TestTransitDepthTask:
    TOLERANCE = 8e-4

    def test_output_exists(self):
        assert get_output_path() is not None, "Expected /root/transit_depth.txt to be created"

    def test_output_is_numeric_and_positive(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output file missing")

        with open(path) as f:
            content = f.read().strip()

        try:
            depth = float(content)
        except ValueError:
            pytest.fail(f"Transit depth is not a valid float: {content}")

        assert 0.0 < depth < 0.02, f"Transit depth should be between 0 and 0.02, got {depth}"

    def test_depth_matches_benchmark(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output file missing")

        with open(path) as f:
            reported = float(f.read().strip())

        benchmark = compute_benchmark_depth()
        assert abs(reported - benchmark) <= self.TOLERANCE, (
            f"Reported depth {reported:.6f} differs from benchmark {benchmark:.6f} "
            f"by more than {self.TOLERANCE:.6f}"
        )

    def test_output_is_rounded_to_six_decimals(self):
        path = get_output_path()
        if path is None:
            pytest.skip("Output file missing")

        with open(path) as f:
            content = f.read().strip()

        assert "." in content, f"Expected decimal output, got {content}"
        decimals = len(content.split(".")[-1])
        assert decimals <= 6, f"Expected at most 6 decimal places, got {content}"
