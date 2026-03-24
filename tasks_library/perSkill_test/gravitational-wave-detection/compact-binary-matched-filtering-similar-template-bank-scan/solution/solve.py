#!/usr/bin/env python3

import pandas as pd
from pycbc.filter import matched_filter
from pycbc.types import FrequencySeries, TimeSeries
from pycbc.waveform import get_td_waveform


STRAIN_PATH = "/root/data/conditioned_strain.csv"
PSD_PATH = "/root/data/noise_psd.csv"
OUTPUT_PATH = "/root/compact_binary_template_bank_scan.csv"
APPROXIMANTS = ["SEOBNRv4_opt", "IMRPhenomD", "TaylorT4"]
MASSES = range(14, 35, 2)
LOW_FREQUENCY_CUTOFF = 20.0


def load_inputs():
    strain_df = pd.read_csv(STRAIN_PATH)
    psd_df = pd.read_csv(PSD_PATH)

    delta_t = float(strain_df["time_s"].iloc[1] - strain_df["time_s"].iloc[0])
    epoch = float(strain_df["time_s"].iloc[0])
    delta_f = float(psd_df["frequency_hz"].iloc[1] - psd_df["frequency_hz"].iloc[0])

    strain = TimeSeries(
        strain_df["strain"].to_numpy(),
        delta_t=delta_t,
        epoch=epoch,
    )
    psd = FrequencySeries(psd_df["psd"].to_numpy(), delta_f=delta_f)
    return strain, psd


def scan_template_bank(strain, psd):
    rows = []
    for approximant in APPROXIMANTS:
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
                peak_snr = float(abs(snr[peak_index]))
                peak_time = float(snr.sample_times[peak_index])
                row = {
                    "approximant": approximant,
                    "snr": peak_snr,
                    "total_mass": float(mass1 + mass2),
                    "peak_time": peak_time,
                }
                if best is None or row["snr"] > best["snr"]:
                    best = row

        if best is None:
            raise RuntimeError(f"No valid templates produced a result for {approximant}")
        rows.append(best)

    rows.sort(key=lambda item: item["approximant"])
    return pd.DataFrame(rows, columns=["approximant", "snr", "total_mass", "peak_time"])


def main():
    strain, psd = load_inputs()
    results = scan_template_bank(strain, psd)
    results.to_csv(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
