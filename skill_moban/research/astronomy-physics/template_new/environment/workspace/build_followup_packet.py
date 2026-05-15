#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.cosmology import FlatLambdaCDM
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.wcs import WCS


# Packet conventions:
# - Use the bundled review rules as the authoritative source for thresholds and
#   distance-model metadata.
# - Keep the support tables and briefing aligned with the final screening
#   labels and derived quantities.


CANDIDATE_PACKET_COLUMNS = [
    "field_id",
    "candidate_id",
    "fits_file",
    "visit_id",
    "filter",
    "x_pixel",
    "y_pixel",
    "ra_deg",
    "dec_deg",
    "gal_l_deg",
    "gal_b_deg",
    "obs_time_iso",
    "obs_time_mjd",
    "snr",
    "quality_flags",
    "screening_label",
    "priority_rank",
]

PHOTOMETRY_COLUMNS = [
    "candidate_id",
    "flux_aperture",
    "flux_err",
    "zeropoint_ab",
    "extinction_mag",
    "exposure_seconds",
    "calibrated_mag",
    "mag_unc",
    "host_id",
    "host_redshift",
    "luminosity_distance_mpc",
    "projected_offset_kpc",
]

HOST_AUDIT_COLUMNS = [
    "candidate_id",
    "nearest_gaia_id",
    "gaia_sep_arcsec",
    "nearest_host_id",
    "host_sep_arcsec",
    "host_match_status",
    "review_reason",
]

DIAGNOSTIC_COLUMNS = [
    "candidate_id",
    "wcs_roundtrip_x_pixel",
    "wcs_roundtrip_y_pixel",
    "gaia_reject_margin_arcsec",
    "host_match_margin_arcsec",
    "screening_score",
]

LABEL_PRIORITY = {
    "high_priority_host_associated": 1,
    "medium_priority_host_associated": 2,
    "review_uncertain_photometry": 3,
    "review_large_host_offset": 4,
    "review_no_host_match": 5,
    "reject_low_snr": 6,
    "reject_foreground_star": 7,
    "reject_bad_measurement": 8,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the NGC 4993 follow-up packet.")
    parser.add_argument("--data", type=Path, required=True, help="Input data root")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    return parser.parse_args()


def load_inputs(data_root: Path) -> dict[str, object]:
    return {
        "detections": pd.read_csv(data_root / "detections" / "candidate_detections.csv"),
        "visits": pd.read_csv(data_root / "observations" / "visit_manifest.tsv", sep="\t"),
        "rules": json.loads((data_root / "observations" / "review_rules.json").read_text(encoding="utf-8")),
        "hosts": pd.read_csv(data_root / "catalogs" / "host_galaxies.tsv", sep="\t"),
        "gaia": Table.read(data_root / "catalogs" / "gaia_foreground_slice.ecsv", format="ascii.ecsv"),
    }


def midpoint_time(obs_start_utc: str, exposure_seconds: float) -> tuple[str, float]:
    midpoint = Time(obs_start_utc, scale="utc") + TimeDelta(exposure_seconds / 2.0, format="sec")
    return midpoint.to_value("isot"), float(midpoint.mjd)


def calibrated_mag(flux_aperture: float, exposure_seconds: float, zeropoint_ab: float, extinction_mag: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return zeropoint_ab - 2.5 * math.log10(flux_aperture / exposure_seconds) - extinction_mag


def magnitude_uncertainty(flux_aperture: float, flux_err: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return 1.0857362047581294 * flux_err / flux_aperture


def build_distance_model(distance_model: dict[str, object]) -> FlatLambdaCDM:
    return FlatLambdaCDM(
        H0=float(distance_model["H0"]),
        Om0=float(distance_model["Om0"]),
        Tcmb0=float(distance_model["Tcmb0"]),
    )


def screening_score(label: str, snr: float, mag_unc: float, projected_offset_kpc: float) -> float:
    penalties = {
        "reject_foreground_star": 10.0,
        "reject_low_snr": 8.0,
        "reject_bad_measurement": 12.0,
        "review_no_host_match": 6.0,
        "review_large_host_offset": 3.0,
        "review_uncertain_photometry": 3.5,
    }
    base_score = snr - projected_offset_kpc - (4.0 * mag_unc)
    return float(base_score - penalties.get(label, 0.0))


def build_outputs(data_root: Path) -> dict[str, object]:
    raise NotImplementedError(
        "Implement the follow-up packet builder so the formal entrypoint writes all required outputs. "
        "Use the bundled review rules, reconstruct sky coordinates from the FITS inputs, normalize the "
        "observation times, derive priority ranks and diagnostic scores from the final screening labels, "
        "keep the support tables and briefing mutually consistent, and report the bundled distance model "
        "in the final briefing."
    )


def write_outputs(bundle: dict[str, object], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    Table.from_pandas(bundle["candidate_followup_packet"]).write(
        output_root / "candidate_followup_packet.ecsv",
        format="ascii.ecsv",
        overwrite=True,
    )
    bundle["photometry_context"].to_csv(
        output_root / "photometry_context.tsv",
        sep="\t",
        index=False,
    )
    bundle["host_association_audit"].to_csv(
        output_root / "host_association_audit.tsv",
        sep="\t",
        index=False,
    )
    bundle["screening_diagnostics"].to_csv(
        output_root / "screening_diagnostics.tsv",
        sep="\t",
        index=False,
    )
    (output_root / "briefing.json").write_text(bundle["briefing_json"], encoding="utf-8")


def main() -> None:
    args = parse_args()
    _ = load_inputs(args.data)
    bundle = build_outputs(args.data)
    write_outputs(bundle, args.output)


if __name__ == "__main__":
    main()
