#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np
import pandas as pd


STRAIN_PATH = Path("/root/data/bns_alert_strain.npz")
PSD_PATH = Path("/root/data/noise_psd.csv")
TEMPLATE_BANK_PATH = Path("/root/data/bns_template_bank.npz")
TEMPLATE_METADATA_PATH = Path("/root/data/template_bank.json")
ALERT_CONTEXT_PATH = Path("/root/data/alert_context.json")
OUTPUT_PATH = Path("/root/bns_early_warning_report.json")


def load_inputs():
    strain_npz = np.load(STRAIN_PATH)
    time_s = strain_npz["time_s"]
    strain = strain_npz["strain"]

    psd_df = pd.read_csv(PSD_PATH)
    metadata = json.loads(TEMPLATE_METADATA_PATH.read_text())
    template_bank = np.load(TEMPLATE_BANK_PATH)
    context = json.loads(ALERT_CONTEXT_PATH.read_text())
    return time_s, strain, psd_df, metadata, template_bank, context


def whiten(series, delta_t, psd_frequency_hz, psd_values):
    freqs = np.fft.rfftfreq(len(series), d=delta_t)
    interp_psd = np.interp(freqs, psd_frequency_hz, psd_values)
    return np.fft.irfft(np.fft.rfft(series) / np.sqrt(interp_psd), n=len(series))


def chirp_mass(mass1, mass2):
    return (mass1 * mass2) ** (3.0 / 5.0) / (mass1 + mass2) ** (1.0 / 5.0)


def main():
    time_s, strain, psd_df, metadata, template_bank, context = load_inputs()
    delta_t = float(time_s[1] - time_s[0])
    psd_frequency_hz = psd_df["frequency_hz"].to_numpy()
    psd_values = psd_df["psd"].to_numpy()
    white_strain = whiten(strain, delta_t, psd_frequency_hz, psd_values)

    best = None
    for item in metadata:
        template_id = item["template_id"]
        template = template_bank[template_id]
        white_template = whiten(template, delta_t, psd_frequency_hz, psd_values)
        snr_series = np.correlate(white_strain, white_template, mode="full") / np.linalg.norm(white_template)

        peak_index = int(np.abs(snr_series).argmax())
        lag = peak_index - (len(white_template) - 1)
        template_end_index = lag + len(white_template) - 1
        if template_end_index < 0 or template_end_index >= len(time_s):
            continue

        candidate = {
            "best_template_id": template_id,
            "mass1_solar_mass": float(item["mass1_solar_mass"]),
            "mass2_solar_mass": float(item["mass2_solar_mass"]),
            "chirp_mass_solar_mass": float(chirp_mass(item["mass1_solar_mass"], item["mass2_solar_mass"])),
            "peak_snr": float(np.abs(snr_series[peak_index])),
            "peak_time_s": float(time_s[template_end_index]),
        }
        candidate["seconds_before_merger"] = float(context["nominal_merger_time_s"] - candidate["peak_time_s"])

        if best is None or candidate["peak_snr"] > best["peak_snr"]:
            best = candidate

    if best is None:
        raise RuntimeError("No template produced a valid matched-filter peak")

    OUTPUT_PATH.write_text(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
