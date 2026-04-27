#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18 as COSMO
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS


ENV = Path(os.environ.get("ENV_ROOT", "/root/environment"))
DATA = ENV / "data"

ASTROMETRY_COLUMNS = [
    "field_id",
    "candidate_id",
    "fits_file",
    "hdu_name",
    "x_pixel",
    "y_pixel",
    "ra_icrs_deg",
    "dec_icrs_deg",
    "gal_l_deg",
    "gal_b_deg",
    "obstime_utc_iso",
    "obstime_mjd",
    "filter",
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
    "calibrated_ab_mag",
    "mag_unc",
    "host_id",
    "host_redshift",
    "luminosity_distance_mpc",
    "absolute_mag",
]

CROSSMATCH_COLUMNS = [
    "candidate_id",
    "nearest_gaia_source_id",
    "gaia_sep_arcsec",
    "nearest_host_id",
    "host_sep_arcsec",
    "nearest_moving_object_id",
    "moving_object_sep_arcsec",
    "match_decision",
    "rejection_reason",
]

DIAGNOSTIC_COLUMNS = [
    "candidate_id",
    "wcs_roundtrip_x_pixel",
    "wcs_roundtrip_y_pixel",
    "gaia_reject_margin_arcsec",
    "host_match_margin_arcsec",
    "moving_object_reject_margin_arcsec",
    "classification_priority",
    "row_signature",
]

CLASSIFICATION_PRIORITY = {
    "reject_quality_flag": 1,
    "reject_low_snr": 2,
    "reject_stellar_counterpart": 3,
    "reject_moving_object": 4,
    "review_no_host": 5,
    "reject_uncertain_photometry": 6,
    "review_faint_host_association": 7,
    "extragalactic_transient": 8,
}

SIGNATURE_DOMAIN = "astropy-transient-triage-kernel-2026-04-27-v3"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_match(coord: SkyCoord, catalog: pd.DataFrame, id_column: str):
    if catalog.empty:
        return "", float("nan"), None
    catalog_coords = SkyCoord(catalog["ra_icrs_deg"].to_numpy(float) * u.deg, catalog["dec_icrs_deg"].to_numpy(float) * u.deg)
    separations = coord.separation(catalog_coords)
    idx = int(np.argmin(separations.arcsec))
    row = catalog.iloc[idx]
    return str(row[id_column]), float(separations[idx].arcsec), row


def classify(row: dict, cfg: dict) -> tuple[str, bool, str]:
    if str(row["quality_flags"]) != "none":
        return "reject_quality_flag", False, "quality_flags"
    if float(row["snr"]) < cfg["min_snr"]:
        return "reject_low_snr", False, "snr_below_threshold"
    if row["gaia_sep_arcsec"] <= cfg["gaia_reject_arcsec"]:
        return "reject_stellar_counterpart", False, "gaia_counterpart"
    if row["moving_object_sep_arcsec"] <= cfg["moving_object_reject_arcsec"]:
        return "reject_moving_object", False, "moving_object_counterpart"
    if not row["host_id"]:
        return "review_no_host", False, "no_host_within_threshold"
    if not np.isfinite(row["mag_unc"]) or row["mag_unc"] > cfg["max_mag_unc"]:
        return "reject_uncertain_photometry", False, "mag_uncertainty"
    if not np.isfinite(row["absolute_mag"]) or row["absolute_mag"] > cfg["reportable_absolute_mag_max"]:
        return "review_faint_host_association", False, "absolute_magnitude_too_faint"
    return "extragalactic_transient", True, "hosted_luminous_transient"


def row_signature(candidate_id, sky, classification, reportable, mag, gaia_id, host_id_raw, moving_id):
    body = (
        f"{SIGNATURE_DOMAIN}|{candidate_id}|{sky.ra.deg:.7f}|{sky.dec.deg:.7f}|{classification}|"
        f"{int(bool(reportable))}|{mag:.6f}|{gaia_id}|{host_id_raw}|{moving_id}"
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def build_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    cfg = load_json(DATA / "calibration" / "triage_config.json")
    detections = pd.read_csv(DATA / "detections" / "detections.csv")
    calibration = pd.read_csv(DATA / "calibration" / "filter_calibration.tsv", sep="\t").set_index("filter")
    gaia = Table.read(DATA / "catalogs" / "gaia_reference.ecsv", format="ascii.ecsv").to_pandas()
    hosts = pd.read_csv(DATA / "catalogs" / "host_galaxies.tsv", sep="\t")
    moving = pd.read_csv(DATA / "catalogs" / "moving_objects.tsv", sep="\t")

    astrometry_rows = []
    photometry_rows = []
    crossmatch_rows = []
    diagnostic_rows = []
    reportable_payload = []

    for det in detections.to_dict("records"):
        with fits.open(DATA / "fits" / det["fits_file"]) as hdul:
            hdu = hdul[det["hdu_name"]]
            header = hdu.header
            wcs = WCS(header)
            sky = wcs.pixel_to_world(float(det["x_pixel"]) - cfg["pixel_origin"], float(det["y_pixel"]) - cfg["pixel_origin"]).icrs
            roundtrip_x, roundtrip_y = wcs.world_to_pixel(sky)
            roundtrip_x += cfg["pixel_origin"]
            roundtrip_y += cfg["pixel_origin"]
            gal = sky.galactic
            obstime = Time(header["DATE-OBS"], scale="utc") + float(header["EXPTIME"]) * u.s / 2
            exposure = float(header["EXPTIME"])
            filter_name = str(header["FILTER"])

        gaia_id, gaia_sep, _ = nearest_match(sky, gaia, "source_id")
        host_id_raw, host_sep, host_row = nearest_match(sky, hosts, "host_id")
        host_id = host_id_raw if host_sep <= cfg["host_match_arcsec"] else ""
        host_redshift = float(host_row["redshift"]) if host_id else float("nan")

        moving_valid = moving[(moving["valid_start_mjd"] <= obstime.mjd) & (moving["valid_end_mjd"] >= obstime.mjd)]
        moving_id, moving_sep, _ = nearest_match(sky, moving_valid, "object_id")

        cal = calibration.loc[filter_name]
        flux = float(det["flux_aperture"])
        flux_err = float(det["flux_err"])
        flux_rate = flux / exposure
        mag = float(cal["zeropoint_ab"]) - 2.5 * np.log10(flux_rate) - float(cal["extinction_mag"])
        mag_unc = 1.0857362047581294 * flux_err / flux if flux > 0 else float("nan")
        if host_id:
            ld_mpc = float(COSMO.luminosity_distance(host_redshift).to_value("Mpc"))
            absolute_mag = mag - float(COSMO.distmod(host_redshift).value)
        else:
            ld_mpc = float("nan")
            absolute_mag = float("nan")

        decision_basis = {
            **det,
            "gaia_sep_arcsec": gaia_sep,
            "moving_object_sep_arcsec": moving_sep,
            "host_id": host_id,
            "mag_unc": mag_unc,
            "absolute_mag": absolute_mag,
        }
        classification, reportable, rejection_reason = classify(decision_basis, cfg)
        match_decision = "accepted" if reportable else "rejected"

        astrometry_rows.append(
            {
                "field_id": det["field_id"],
                "candidate_id": det["candidate_id"],
                "fits_file": det["fits_file"],
                "hdu_name": det["hdu_name"],
                "x_pixel": det["x_pixel"],
                "y_pixel": det["y_pixel"],
                "ra_icrs_deg": sky.ra.deg,
                "dec_icrs_deg": sky.dec.deg,
                "gal_l_deg": gal.l.deg,
                "gal_b_deg": gal.b.deg,
                "obstime_utc_iso": obstime.utc.isot,
                "obstime_mjd": float(obstime.utc.mjd),
                "filter": filter_name,
                "snr": det["snr"],
                "quality_flags": det["quality_flags"],
                "classification": classification,
                "reportable": bool(reportable),
            }
        )
        photometry_rows.append(
            {
                "candidate_id": det["candidate_id"],
                "flux_aperture": flux,
                "flux_err": flux_err,
                "zeropoint_ab": float(cal["zeropoint_ab"]),
                "extinction_mag": float(cal["extinction_mag"]),
                "calibrated_ab_mag": mag,
                "mag_unc": mag_unc,
                "host_id": host_id,
                "host_redshift": host_redshift,
                "luminosity_distance_mpc": ld_mpc,
                "absolute_mag": absolute_mag,
            }
        )
        crossmatch_rows.append(
            {
                "candidate_id": det["candidate_id"],
                "nearest_gaia_source_id": gaia_id,
                "gaia_sep_arcsec": gaia_sep,
                "nearest_host_id": host_id_raw,
                "host_sep_arcsec": host_sep,
                "nearest_moving_object_id": moving_id,
                "moving_object_sep_arcsec": moving_sep,
                "match_decision": match_decision,
                "rejection_reason": rejection_reason,
            }
        )
        diagnostic_rows.append(
            {
                "candidate_id": det["candidate_id"],
                "wcs_roundtrip_x_pixel": float(roundtrip_x),
                "wcs_roundtrip_y_pixel": float(roundtrip_y),
                "gaia_reject_margin_arcsec": float(gaia_sep - cfg["gaia_reject_arcsec"]),
                "host_match_margin_arcsec": float(cfg["host_match_arcsec"] - host_sep),
                "moving_object_reject_margin_arcsec": (
                    float(moving_sep - cfg["moving_object_reject_arcsec"]) if np.isfinite(moving_sep) else float("nan")
                ),
                "classification_priority": CLASSIFICATION_PRIORITY[classification],
                "row_signature": row_signature(
                    det["candidate_id"],
                    sky,
                    classification,
                    reportable,
                    mag,
                    gaia_id,
                    host_id_raw,
                    moving_id,
                ),
            }
        )
        if reportable:
            reportable_payload.append(
                {
                    "candidate_id": det["candidate_id"],
                    "field_id": det["field_id"],
                    "filter": filter_name,
                    "ra_icrs_deg": sky.ra.deg,
                    "dec_icrs_deg": sky.dec.deg,
                    "obstime_utc_iso": obstime.utc.isot,
                    "calibrated_ab_mag": mag,
                    "classification": classification,
                    "primary_evidence": {
                        "host_id": host_id,
                        "host_redshift": host_redshift,
                        "absolute_mag": absolute_mag,
                        "snr": float(det["snr"]),
                    },
                }
            )

    astrometry = pd.DataFrame(astrometry_rows, columns=ASTROMETRY_COLUMNS)
    photometry = pd.DataFrame(photometry_rows, columns=PHOTOMETRY_COLUMNS)
    crossmatch = pd.DataFrame(crossmatch_rows, columns=CROSSMATCH_COLUMNS)
    diagnostics = pd.DataFrame(diagnostic_rows, columns=DIAGNOSTIC_COLUMNS)
    classification_summary = dict(sorted(Counter(astrometry["classification"]).items()))

    response = requests.post(cfg["field_context_url"], json={"candidates": reportable_payload}, timeout=10)
    response.raise_for_status()
    field_context = response.json()

    report = {
        "n_input_detections": int(len(astrometry)),
        "n_reportable_candidates": int(astrometry["reportable"].sum()),
        "coordinate_frame": "ICRS degrees from FITS WCS; Galactic coordinates are derived from the same ICRS SkyCoord.",
        "time_scale": "UTC exposure midpoint ISO timestamps with matching Astropy MJD values.",
        "cosmology": "Astropy Planck18",
        "classification_summary": classification_summary,
        "field_context_summary": field_context,
        "reportable_candidates": sorted(reportable_payload, key=lambda item: item["candidate_id"]),
        "notes": [
            "Detector coordinates in the detection table use FITS 1-based pixel convention.",
            "Catalog matching uses spherical angular separations and configured arcsecond thresholds.",
        ],
    }
    return astrometry, photometry, crossmatch, diagnostics, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/root/answer")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    astrometry, photometry, crossmatch, diagnostics, report = build_outputs()
    Table.from_pandas(astrometry).write(output / "astrometric_candidates.ecsv", format="ascii.ecsv", overwrite=True)
    photometry.to_csv(output / "photometry_summary.tsv", sep="\t", index=False, float_format="%.10g")
    crossmatch.to_csv(output / "crossmatch_audit.tsv", sep="\t", index=False, float_format="%.10g")
    diagnostics.to_csv(output / "triage_diagnostics.tsv", sep="\t", index=False, float_format="%.10g")
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "field_context.json").write_text(
        json.dumps(report["field_context_summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
