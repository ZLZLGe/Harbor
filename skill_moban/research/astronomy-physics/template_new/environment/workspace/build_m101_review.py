#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import astropy.units as u
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.cosmology import FlatLambdaCDM
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.wcs import WCS


REVIEW_COSMOLOGY = FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=2.725)

CANDIDATE_COLUMNS = [
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
    "classification",
    "reportable",
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
    "distance_mpc",
    "absolute_mag",
]

CROSSMATCH_COLUMNS = [
    "candidate_id",
    "nearest_gaia_id",
    "gaia_sep_arcsec",
    "nearest_host_id",
    "host_sep_arcsec",
    "match_decision",
    "rejection_reason",
]

DIAGNOSTIC_COLUMNS = [
    "candidate_id",
    "wcs_roundtrip_x_pixel",
    "wcs_roundtrip_y_pixel",
    "gaia_reject_margin_arcsec",
    "host_match_margin_arcsec",
    "classification_priority",
]


def midpoint_time(start_iso: str, exposure_seconds: float) -> tuple[str, float]:
    timestamp = Time(start_iso, scale="utc") + TimeDelta(exposure_seconds / 2.0, format="sec")
    return timestamp.to_value("isot", subfmt="date_hms"), float(timestamp.mjd)


def calibrated_mag(
    flux_aperture: float,
    exposure_seconds: float,
    zeropoint_ab: float,
    extinction_mag: float,
) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return zeropoint_ab - 2.5 * math.log10(flux_aperture / exposure_seconds) - extinction_mag


def magnitude_uncertainty(flux_aperture: float, flux_err: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return 1.0857362047581294 * flux_err / flux_aperture


def classification_priority() -> dict[str, int]:
    ordered = [
        "reject_bad_measurement",
        "reject_low_snr",
        "reject_foreground_star",
        "review_no_host",
        "reject_uncertain_photometry",
        "review_faint_host_association",
        "extragalactic_candidate",
    ]
    return {name: index + 1 for index, name in enumerate(ordered)}


def classify_candidate(
    *,
    quality_flags: str,
    snr: float,
    min_snr: float,
    gaia_sep_arcsec: float,
    gaia_reject_arcsec: float,
    host_sep_arcsec: float,
    host_match_arcsec: float,
    mag_unc: float,
    max_mag_unc: float,
    absolute_mag: float,
    reportable_absolute_mag_max: float,
) -> str:
    if quality_flags != "none":
        return "reject_bad_measurement"
    if snr < min_snr:
        return "reject_low_snr"
    if gaia_sep_arcsec <= gaia_reject_arcsec:
        return "reject_foreground_star"
    if host_sep_arcsec > host_match_arcsec:
        return "review_no_host"
    if not math.isfinite(mag_unc) or mag_unc > max_mag_unc:
        return "reject_uncertain_photometry"
    if not math.isfinite(absolute_mag) or absolute_mag > reportable_absolute_mag_max:
        return "review_faint_host_association"
    return "extragalactic_candidate"


def load_inputs(data_root: Path) -> dict[str, object]:
    detections = pd.read_csv(data_root / "detections" / "candidate_detections.csv")
    visits = pd.read_csv(data_root / "observations" / "visit_manifest.tsv", sep="\t")
    config = json.loads((data_root / "observations" / "review_rules.json").read_text(encoding="utf-8"))
    gaia = Table.read(str(data_root / "catalogs" / "gaia_m101_cone.ecsv"), format="ascii.ecsv")
    hosts = pd.read_csv(data_root / "catalogs" / "host_galaxies.tsv", sep="\t")

    visit_by_id = {row["visit_id"]: row for _, row in visits.iterrows()}
    wcs_by_file = {
        row["fits_file"]: WCS(fits.getheader(data_root / "fits" / row["fits_file"]))
        for _, row in visits.iterrows()
    }
    gaia_id_column = "gaia_id" if "gaia_id" in gaia.colnames else "source_id"
    gaia_coords = SkyCoord(ra=gaia["ra_deg"] * u.deg, dec=gaia["dec_deg"] * u.deg, frame="icrs")
    host_coords = SkyCoord(
        ra=hosts["ra_deg"].to_numpy() * u.deg,
        dec=hosts["dec_deg"].to_numpy() * u.deg,
        frame="icrs",
    )

    return {
        "detections": detections,
        "visits": visits,
        "config": config,
        "gaia": gaia,
        "hosts": hosts,
        "visit_by_id": visit_by_id,
        "wcs_by_file": wcs_by_file,
        "gaia_id_column": gaia_id_column,
        "gaia_coords": gaia_coords,
        "host_coords": host_coords,
    }


def empty_bundle() -> dict[str, object]:
    return {
        "candidate_review": pd.DataFrame(columns=CANDIDATE_COLUMNS),
        "photometry_summary": pd.DataFrame(columns=PHOTOMETRY_COLUMNS),
        "crossmatch_audit": pd.DataFrame(columns=CROSSMATCH_COLUMNS),
        "triage_diagnostics": pd.DataFrame(columns=DIAGNOSTIC_COLUMNS),
        "report": {
            "field_id": "",
            "n_input_candidates": 0,
            "n_reportable_candidates": 0,
            "coordinate_frame": "ICRS",
            "time_scale": "UTC midpoint with companion MJD",
            "cosmology": "FlatLambdaCDM(H0=70 km s^-1 Mpc^-1, Om0=0.3, Tcmb0=2.725 K)",
            "classification_summary": {},
            "reportable_candidates": [],
            "notes": [],
        },
    }


def build_bundle(data_root: Path) -> dict[str, object]:
    inputs = load_inputs(data_root)

    # Required work for the task:
    # 1. Rebuild detector-space positions into ICRS sky coordinates from the FITS WCS.
    # 2. Normalize observation times to UTC midpoint ISO strings and companion MJDs.
    # 3. Cross-match each candidate against Gaia and nearest host-galaxy entries.
    # 4. Compute calibrated photometry, host-distance context, and diagnostics.
    # 5. Classify each candidate from review_rules.json and assemble the final bundle.
    #
    # Keep the scientific chain internally consistent across all four tables and report.json.
    # The formal entrypoint must write all required deliverables to the output directory.

    _ = inputs
    _ = empty_bundle
    raise SystemExit(
        "Review bundle scaffold only. Implement the full M101 review pipeline in this file "
        "using the bundled FITS WCS, catalogs, observation metadata, and review rules."
    )


def write_bundle(bundle: dict[str, object], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    Table.from_pandas(bundle["candidate_review"]).write(
        output_root / "candidate_review.ecsv",
        format="ascii.ecsv",
        overwrite=True,
    )
    bundle["photometry_summary"].to_csv(output_root / "photometry_summary.tsv", sep="\t", index=False)
    bundle["crossmatch_audit"].to_csv(output_root / "crossmatch_audit.tsv", sep="\t", index=False)
    bundle["triage_diagnostics"].to_csv(output_root / "triage_diagnostics.tsv", sep="\t", index=False)
    (output_root / "report.json").write_text(
        json.dumps(bundle["report"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bundle = build_bundle(Path(args.data))
    write_bundle(bundle, Path(args.output))


if __name__ == "__main__":
    main()
