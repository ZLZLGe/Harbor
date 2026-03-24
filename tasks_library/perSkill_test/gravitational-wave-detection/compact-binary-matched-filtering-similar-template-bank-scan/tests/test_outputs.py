from pathlib import Path

import pandas as pd
import pytest
from pycbc.filter import matched_filter
from pycbc.types import FrequencySeries, TimeSeries
from pycbc.waveform import get_td_waveform


OUTPUT_FILE = Path("/root/compact_binary_template_bank_scan.csv")
STRAIN_FILE = Path("/root/data/conditioned_strain.csv")
PSD_FILE = Path("/root/data/noise_psd.csv")
EXPECTED_COLUMNS = ["approximant", "snr", "total_mass", "peak_time"]
EXPECTED_APPROXIMANTS = ["IMRPhenomD", "SEOBNRv4_opt", "TaylorT4"]
SNR_TOLERANCE = 0.25
TOTAL_MASS_TOLERANCE = 0.1
PEAK_TIME_TOLERANCE = 0.002
LOW_FREQUENCY_CUTOFF = 20.0
MASSES = range(14, 35, 2)


def load_inputs():
    strain_df = pd.read_csv(STRAIN_FILE)
    psd_df = pd.read_csv(PSD_FILE)

    strain = TimeSeries(
        strain_df["strain"].to_numpy(),
        delta_t=float(strain_df["time_s"].iloc[1] - strain_df["time_s"].iloc[0]),
        epoch=float(strain_df["time_s"].iloc[0]),
    )
    psd = FrequencySeries(
        psd_df["psd"].to_numpy(),
        delta_f=float(psd_df["frequency_hz"].iloc[1] - psd_df["frequency_hz"].iloc[0]),
    )
    return strain, psd


def recompute_expected_results():
    strain, psd = load_inputs()
    rows = []

    for approximant in ["SEOBNRv4_opt", "IMRPhenomD", "TaylorT4"]:
        best = None
        for mass1 in MASSES:
            for mass2 in MASSES:
                if mass1 < mass2:
                    continue
                try:
                    hp, _ = get_td_waveform(
                        approximant=approximant,
                        mass1=mass1,
                        mass2=mass2,
                        delta_t=strain.delta_t,
                        f_lower=LOW_FREQUENCY_CUTOFF,
                    )
                except Exception:
                    continue

                hp.resize(len(strain))
                template = hp.cyclic_time_shift(hp.start_time)
                snr = matched_filter(
                    template,
                    strain,
                    psd=psd,
                    low_frequency_cutoff=LOW_FREQUENCY_CUTOFF,
                )
                peak_index = abs(snr).numpy().argmax()
                candidate = {
                    "approximant": approximant,
                    "snr": float(abs(snr[peak_index])),
                    "total_mass": float(mass1 + mass2),
                    "peak_time": float(snr.sample_times[peak_index]),
                }
                if best is None or candidate["snr"] > best["snr"]:
                    best = candidate

        assert best is not None, f"no valid template found for {approximant}"
        rows.append(best)

    return pd.DataFrame(rows).sort_values("approximant").reset_index(drop=True)


@pytest.fixture
def output_df():
    assert OUTPUT_FILE.exists(), f"Output file not found: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE)


@pytest.fixture(scope="module")
def expected_df():
    return recompute_expected_results()


def test_columns(output_df):
    assert list(output_df.columns) == EXPECTED_COLUMNS


def test_row_count_and_order(output_df):
    assert len(output_df) == 3
    assert output_df["approximant"].tolist() == EXPECTED_APPROXIMANTS


def test_types_and_ranges(output_df):
    assert pd.api.types.is_string_dtype(output_df["approximant"])
    for column in ["snr", "total_mass", "peak_time"]:
        assert pd.api.types.is_numeric_dtype(output_df[column]), f"{column} must be numeric"
    assert (output_df["snr"] > 0).all()
    assert (output_df["total_mass"] >= 28).all()
    assert (output_df["total_mass"] <= 68).all()


def test_matches_expected(output_df, expected_df):
    failures = []
    expected_lookup = {row["approximant"]: row for _, row in expected_df.iterrows()}
    for _, row in output_df.iterrows():
        expected = expected_lookup[row["approximant"]]

        snr_diff = abs(row["snr"] - expected["snr"])
        if snr_diff > SNR_TOLERANCE:
            failures.append(
                f"{row['approximant']} snr mismatch: got {row['snr']:.6f}, expected {expected['snr']:.6f}"
            )

        total_mass_diff = abs(row["total_mass"] - expected["total_mass"])
        if total_mass_diff > TOTAL_MASS_TOLERANCE:
            failures.append(
                f"{row['approximant']} total_mass mismatch: got {row['total_mass']:.6f}, expected {expected['total_mass']:.6f}"
            )

        peak_time_diff = abs(row["peak_time"] - expected["peak_time"])
        if peak_time_diff > PEAK_TIME_TOLERANCE:
            failures.append(
                f"{row['approximant']} peak_time mismatch: got {row['peak_time']:.6f}, expected {expected['peak_time']:.6f}"
            )

    if failures:
        pytest.fail("\n".join(failures))
