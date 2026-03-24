import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


OUTPUT_FILE = Path("/root/bns_early_warning_report.json")
STRAIN_PATH = Path("/root/data/bns_alert_strain.npz")
PSD_PATH = Path("/root/data/noise_psd.csv")
TEMPLATE_BANK_PATH = Path("/root/data/bns_template_bank.npz")
TEMPLATE_METADATA_PATH = Path("/root/data/template_bank.json")
ALERT_CONTEXT_PATH = Path("/root/data/alert_context.json")

EXPECTED_KEYS = [
    "best_template_id",
    "mass1_solar_mass",
    "mass2_solar_mass",
    "chirp_mass_solar_mass",
    "peak_snr",
    "peak_time_s",
    "seconds_before_merger",
]
SNR_TOLERANCE = 1e-6
MASS_TOLERANCE = 1e-9
TIME_TOLERANCE = 1e-9


def whiten(series, delta_t, psd_frequency_hz, psd_values):
    freqs = np.fft.rfftfreq(len(series), d=delta_t)
    interp_psd = np.interp(freqs, psd_frequency_hz, psd_values)
    return np.fft.irfft(np.fft.rfft(series) / np.sqrt(interp_psd), n=len(series))


def chirp_mass(mass1, mass2):
    return (mass1 * mass2) ** (3.0 / 5.0) / (mass1 + mass2) ** (1.0 / 5.0)


def recompute_expected():
    strain_npz = np.load(STRAIN_PATH)
    time_s = strain_npz["time_s"]
    strain = strain_npz["strain"]
    delta_t = float(time_s[1] - time_s[0])

    psd_df = pd.read_csv(PSD_PATH)
    psd_frequency_hz = psd_df["frequency_hz"].to_numpy()
    psd_values = psd_df["psd"].to_numpy()

    metadata = json.loads(TEMPLATE_METADATA_PATH.read_text())
    template_bank = np.load(TEMPLATE_BANK_PATH)
    context = json.loads(ALERT_CONTEXT_PATH.read_text())
    white_strain = whiten(strain, delta_t, psd_frequency_hz, psd_values)

    best = None
    for item in metadata:
        template = template_bank[item["template_id"]]
        white_template = whiten(template, delta_t, psd_frequency_hz, psd_values)
        snr_series = np.correlate(white_strain, white_template, mode="full") / np.linalg.norm(white_template)

        peak_index = int(np.abs(snr_series).argmax())
        lag = peak_index - (len(white_template) - 1)
        template_end_index = lag + len(white_template) - 1
        assert 0 <= template_end_index < len(time_s)

        candidate = {
            "best_template_id": item["template_id"],
            "mass1_solar_mass": float(item["mass1_solar_mass"]),
            "mass2_solar_mass": float(item["mass2_solar_mass"]),
            "chirp_mass_solar_mass": float(chirp_mass(item["mass1_solar_mass"], item["mass2_solar_mass"])),
            "peak_snr": float(np.abs(snr_series[peak_index])),
            "peak_time_s": float(time_s[template_end_index]),
        }
        candidate["seconds_before_merger"] = float(context["nominal_merger_time_s"] - candidate["peak_time_s"])

        if best is None or candidate["peak_snr"] > best["peak_snr"]:
            best = candidate

    assert best is not None
    return best


@pytest.fixture(scope="module")
def output_payload():
    assert OUTPUT_FILE.exists(), f"Output file not found: {OUTPUT_FILE}"
    return json.loads(OUTPUT_FILE.read_text())


@pytest.fixture(scope="module")
def expected_payload():
    return recompute_expected()


def test_output_keys(output_payload):
    assert list(output_payload.keys()) == EXPECTED_KEYS


def test_output_value_types(output_payload):
    assert isinstance(output_payload["best_template_id"], str)
    for key in EXPECTED_KEYS[1:]:
        assert isinstance(output_payload[key], (int, float)), f"{key} must be numeric"


def test_output_ranges(output_payload):
    assert 1.0 <= output_payload["mass1_solar_mass"] <= 1.5
    assert 1.0 <= output_payload["mass2_solar_mass"] <= 1.5
    assert output_payload["peak_snr"] > 0.0
    assert output_payload["seconds_before_merger"] > 0.0
    assert output_payload["peak_time_s"] < 28.0


def test_matches_expected(output_payload, expected_payload):
    assert output_payload["best_template_id"] == expected_payload["best_template_id"]

    for key in ["mass1_solar_mass", "mass2_solar_mass", "chirp_mass_solar_mass"]:
        assert abs(output_payload[key] - expected_payload[key]) <= MASS_TOLERANCE, key

    assert abs(output_payload["peak_snr"] - expected_payload["peak_snr"]) <= SNR_TOLERANCE
    assert abs(output_payload["peak_time_s"] - expected_payload["peak_time_s"]) <= TIME_TOLERANCE
    assert abs(output_payload["seconds_before_merger"] - expected_payload["seconds_before_merger"]) <= TIME_TOLERANCE
