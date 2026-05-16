#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd
import numpy as np
from astropy.coordinates import AltAz, SkyCoord
from astropy.cosmology import FlatLambdaCDM
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.utils import iers
from astropy.wcs import WCS


iers.conf.auto_download = False
iers.conf.auto_max_age = None


CANDIDATE_PACKET_COLUMNS = [
    "field_id",
    "candidate_id",
    "fits_file",
    "visit_id",
    "filter",
    "x_seed",
    "y_seed",
    "x_pixel",
    "y_pixel",
    "ra_deg",
    "dec_deg",
    "gal_l_deg",
    "gal_b_deg",
    "obs_time_iso",
    "obs_time_mjd",
    "obs_time_bjd_tdb",
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
    "altitude_deg",
    "airmass",
    "host_id",
    "host_redshift",
    "luminosity_distance_mpc",
    "projected_offset_kpc",
]

HOST_AUDIT_COLUMNS = [
    "candidate_id",
    "nearest_gaia_id",
    "gaia_reference_epoch_jyear",
    "gaia_sep_arcsec",
    "nearest_host_id",
    "host_sep_arcsec",
    "host_match_status",
    "review_reason",
]

DIAGNOSTIC_COLUMNS = [
    "candidate_id",
    "seed_offset_pix",
    "wcs_roundtrip_x_pixel",
    "wcs_roundtrip_y_pixel",
    "barycentric_correction_sec",
    "gaia_epoch_shift_arcsec",
    "gaia_reject_margin_arcsec",
    "host_match_margin_arcsec",
    "screening_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the NGC 4993 follow-up packet.")
    parser.add_argument("--data", type=Path, required=True, help="Input data root")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    return parser.parse_args()


def load_inputs(data_root: Path) -> dict[str, object]:
    return {
        "seeds": pd.read_csv(data_root / "detections" / "candidate_seeds.csv"),
        "visits": pd.read_csv(data_root / "observations" / "visit_manifest.tsv", sep="\t"),
        "rules": json.loads((data_root / "observations" / "review_rules.json").read_text(encoding="utf-8")),
        "host_coordinates": Table.read(data_root / "catalogs" / "host_coordinates.ecsv", format="ascii.ecsv").to_pandas(),
        "host_properties": Table.read(data_root / "catalogs" / "host_properties.fits", format="fits").to_pandas(),
        "gaia": Table.read(data_root / "catalogs" / "gaia_foreground_slice.ecsv", format="ascii.ecsv"),
    }


def decode_if_bytes(value: object) -> object:
    return value.decode() if isinstance(value, bytes) else value


def decode_bytes_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        out[column] = out[column].map(decode_if_bytes)
    return out


def midpoint_time(obs_start_value: str, time_format: str, time_scale: str, exposure_seconds: float) -> tuple[str, float]:
    start = Time(obs_start_value, format=time_format, scale=time_scale)
    midpoint = start + TimeDelta(exposure_seconds / 2.0, format="sec")
    midpoint_utc = midpoint.utc
    return midpoint_utc.to_value("isot"), float(midpoint_utc.mjd)


def calibrated_mag(flux_aperture: float, exposure_seconds: float, zeropoint_ab: float, extinction_mag: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return zeropoint_ab - 2.5 * math.log10(flux_aperture / exposure_seconds) - extinction_mag


def magnitude_uncertainty(flux_aperture: float, flux_err: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return 1.0857362047581294 * flux_err / flux_aperture


def build_outputs(data_root: Path) -> dict[str, object]:
    raise NotImplementedError(
        "Implement the follow-up packet builder so the formal entrypoint writes all required outputs."
    )


def validate_bundle(bundle: dict[str, object]) -> None:
    required = {
        "candidate_followup_packet": CANDIDATE_PACKET_COLUMNS,
        "photometry_context": PHOTOMETRY_COLUMNS,
        "host_association_audit": HOST_AUDIT_COLUMNS,
        "screening_diagnostics": DIAGNOSTIC_COLUMNS,
    }
    for key, columns in required.items():
        frame = bundle.get(key)
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f"{key} must be a pandas DataFrame")
        if list(frame.columns) != columns:
            raise ValueError(f"{key} columns do not match the required contract")
    briefing_json = bundle.get("briefing_json")
    if not isinstance(briefing_json, str):
        raise TypeError("briefing_json must be a JSON string")
    json.loads(briefing_json)


def write_outputs(bundle: dict[str, object], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    Table.from_pandas(bundle["candidate_followup_packet"]).write(
        output_root / "candidate_followup_packet.ecsv",
        format="ascii.ecsv",
        overwrite=True,
    )
    bundle["photometry_context"].to_csv(output_root / "photometry_context.tsv", sep="\t", index=False)
    bundle["host_association_audit"].to_csv(output_root / "host_association_audit.tsv", sep="\t", index=False)
    bundle["screening_diagnostics"].to_csv(output_root / "screening_diagnostics.tsv", sep="\t", index=False)
    (output_root / "briefing.json").write_text(bundle["briefing_json"], encoding="utf-8")


def main() -> None:
    args = parse_args()
    _ = load_inputs(args.data)
    bundle = build_outputs(args.data)
    validate_bundle(bundle)
    write_outputs(bundle, args.output)


if __name__ == "__main__":
    main()
