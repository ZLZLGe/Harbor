#!/usr/bin/env python3
"""Astropy-based diagnostic probe for the transient triage task.

The probe recomputes row-level quantities from the public FITS, detection,
catalog, and calibration inputs. It is meant for debugging a solver's formal
pipeline output; it does not read tests or hidden expected files.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18 as COSMO
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS


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


def nearest(coord, catalog, id_column):
    if catalog.empty:
        return "", float("nan"), None
    catalog_coords = SkyCoord(catalog["ra_icrs_deg"].to_numpy(float) * u.deg, catalog["dec_icrs_deg"].to_numpy(float) * u.deg)
    separations = coord.separation(catalog_coords)
    idx = int(np.argmin(separations.arcsec))
    row = catalog.iloc[idx]
    return str(row[id_column]), float(separations[idx].arcsec), row


def classify(row, cfg):
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


def reference(env_root):
    data = env_root / "data"
    cfg = json.loads((data / "calibration" / "triage_config.json").read_text(encoding="utf-8"))
    detections = pd.read_csv(data / "detections" / "detections.csv")
    calibration = pd.read_csv(data / "calibration" / "filter_calibration.tsv", sep="\t").set_index("filter")
    gaia = Table.read(data / "catalogs" / "gaia_reference.ecsv", format="ascii.ecsv").to_pandas()
    hosts = pd.read_csv(data / "catalogs" / "host_galaxies.tsv", sep="\t")
    moving = pd.read_csv(data / "catalogs" / "moving_objects.tsv", sep="\t")

    astrometry_rows = []
    photometry_rows = []
    crossmatch_rows = []
    diagnostic_rows = []
    for det in detections.to_dict("records"):
        with fits.open(data / "fits" / det["fits_file"]) as hdul:
            hdu = hdul[det["hdu_name"]]
            wcs = WCS(hdu.header)
            sky = wcs.pixel_to_world(
                float(det["x_pixel"]) - cfg["pixel_origin"],
                float(det["y_pixel"]) - cfg["pixel_origin"],
            ).icrs
            roundtrip_x, roundtrip_y = wcs.world_to_pixel(sky)
            roundtrip_x += cfg["pixel_origin"]
            roundtrip_y += cfg["pixel_origin"]
            gal = sky.galactic
            obstime = Time(hdu.header["DATE-OBS"], scale="utc") + float(hdu.header["EXPTIME"]) * u.s / 2
            exposure = float(hdu.header["EXPTIME"])
            filter_name = str(hdu.header["FILTER"])

        gaia_id, gaia_sep, _ = nearest(sky, gaia, "source_id")
        host_id_raw, host_sep, host_row = nearest(sky, hosts, "host_id")
        host_id = host_id_raw if host_sep <= cfg["host_match_arcsec"] else ""
        host_redshift = float(host_row["redshift"]) if host_id else float("nan")
        moving_valid = moving[(moving["valid_start_mjd"] <= obstime.mjd) & (moving["valid_end_mjd"] >= obstime.mjd)]
        moving_id, moving_sep, _ = nearest(sky, moving_valid, "object_id")

        cal = calibration.loc[filter_name]
        flux = float(det["flux_aperture"])
        flux_err = float(det["flux_err"])
        mag = float(cal["zeropoint_ab"]) - 2.5 * np.log10(flux / exposure) - float(cal["extinction_mag"])
        mag_unc = 1.0857362047581294 * flux_err / flux if flux > 0 else float("nan")
        if host_id:
            ld_mpc = float(COSMO.luminosity_distance(host_redshift).to_value("Mpc"))
            absolute_mag = mag - float(COSMO.distmod(host_redshift).value)
        else:
            ld_mpc = float("nan")
            absolute_mag = float("nan")

        classification, reportable, rejection = classify(
            {
                **det,
                "gaia_sep_arcsec": gaia_sep,
                "moving_object_sep_arcsec": moving_sep,
                "host_id": host_id,
                "mag_unc": mag_unc,
                "absolute_mag": absolute_mag,
            },
            cfg,
        )
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
                "match_decision": "accepted" if reportable else "rejected",
                "rejection_reason": rejection,
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

    return {
        "astrometry": pd.DataFrame(astrometry_rows, columns=ASTROMETRY_COLUMNS),
        "photometry": pd.DataFrame(photometry_rows),
        "crossmatch": pd.DataFrame(crossmatch_rows),
        "diagnostics": pd.DataFrame(diagnostic_rows, columns=DIAGNOSTIC_COLUMNS),
    }


def read_astrometry(path):
    frame = Table.read(path, format="ascii.ecsv").to_pandas()
    if frame["reportable"].dtype != bool:
        frame["reportable"] = frame["reportable"].map(lambda value: str(value).lower() == "true")
    return frame


def audit(env_root, output):
    expected = reference(env_root)
    problems = []
    actual_astrometry = read_astrometry(output / "astrometric_candidates.ecsv").set_index("candidate_id")
    actual_photometry = pd.read_csv(output / "photometry_summary.tsv", sep="\t").set_index("candidate_id")
    actual_crossmatch = pd.read_csv(output / "crossmatch_audit.tsv", sep="\t").fillna("").set_index("candidate_id")
    actual_diagnostics = pd.read_csv(output / "triage_diagnostics.tsv", sep="\t").fillna("").set_index("candidate_id")

    for candidate_id, row in expected["astrometry"].set_index("candidate_id").iterrows():
        got = actual_astrometry.loc[candidate_id]
        for column in ["ra_icrs_deg", "dec_icrs_deg", "gal_l_deg", "gal_b_deg"]:
            if abs(float(got[column]) - row[column]) > 2e-7:
                problems.append(f"{candidate_id}: {column} expected {row[column]:.10f}, got {float(got[column]):.10f}")
        if got["obstime_utc_iso"] != row["obstime_utc_iso"]:
            problems.append(f"{candidate_id}: obstime_utc_iso expected {row['obstime_utc_iso']}, got {got['obstime_utc_iso']}")
        if got["classification"] != row["classification"] or bool(got["reportable"]) != bool(row["reportable"]):
            problems.append(
                f"{candidate_id}: classification/reportable expected {row['classification']}/{row['reportable']}, "
                f"got {got['classification']}/{got['reportable']}"
            )

    for candidate_id, row in expected["photometry"].set_index("candidate_id").iterrows():
        got = actual_photometry.loc[candidate_id]
        for column in ["calibrated_ab_mag", "mag_unc", "luminosity_distance_mpc", "absolute_mag"]:
            if np.isfinite(row[column]) and abs(float(got[column]) - row[column]) > 1e-6:
                problems.append(f"{candidate_id}: {column} expected {row[column]:.10f}, got {float(got[column]):.10f}")

    for candidate_id, row in expected["crossmatch"].set_index("candidate_id").iterrows():
        got = actual_crossmatch.loc[candidate_id]
        for column in ["gaia_sep_arcsec", "host_sep_arcsec", "moving_object_sep_arcsec"]:
            if np.isfinite(row[column]) and abs(float(got[column]) - row[column]) > 2e-4:
                problems.append(f"{candidate_id}: {column} expected {row[column]:.6f}, got {float(got[column]):.6f}")
        for column in ["nearest_gaia_source_id", "nearest_host_id", "nearest_moving_object_id"]:
            if str(got[column]) != str(row[column]):
                problems.append(f"{candidate_id}: {column} expected {row[column]}, got {got[column]}")

    for candidate_id, row in expected["diagnostics"].set_index("candidate_id").iterrows():
        got = actual_diagnostics.loc[candidate_id]
        for column in ["wcs_roundtrip_x_pixel", "wcs_roundtrip_y_pixel", "gaia_reject_margin_arcsec", "host_match_margin_arcsec"]:
            if abs(float(got[column]) - row[column]) > 2e-6:
                problems.append(f"{candidate_id}: {column} expected {row[column]:.8f}, got {float(got[column]):.8f}")
        if np.isfinite(row["moving_object_reject_margin_arcsec"]):
            if abs(float(got["moving_object_reject_margin_arcsec"]) - row["moving_object_reject_margin_arcsec"]) > 2e-6:
                problems.append(
                    f"{candidate_id}: moving_object_reject_margin_arcsec expected "
                    f"{row['moving_object_reject_margin_arcsec']:.8f}, got {float(got['moving_object_reject_margin_arcsec']):.8f}"
                )
        if int(got["classification_priority"]) != int(row["classification_priority"]):
            problems.append(f"{candidate_id}: classification_priority expected {row['classification_priority']}, got {got['classification_priority']}")
        if str(got["row_signature"]) != row["row_signature"]:
            problems.append(f"{candidate_id}: row_signature expected {row['row_signature']}, got {got['row_signature']}")

    summary = {
        "n_expected_rows": int(len(expected["astrometry"])),
        "classification_summary": dict(sorted(Counter(expected["astrometry"]["classification"]).items())),
        "reportable_candidate_ids": expected["astrometry"].loc[
            expected["astrometry"]["reportable"], "candidate_id"
        ].tolist(),
        "problems": problems,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-root", default="/root/environment")
    parser.add_argument("--output", default="/root/answer")
    parser.add_argument("--audit-output", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    env_root = Path(args.env_root)
    output = Path(args.output)
    if args.audit_output:
        raise SystemExit(audit(env_root, output))
    ref = reference(env_root)
    print(
        json.dumps(
            {
                "n_expected_rows": int(len(ref["astrometry"])),
                "classification_summary": dict(sorted(Counter(ref["astrometry"]["classification"]).items())),
                "reportable_candidate_ids": ref["astrometry"].loc[ref["astrometry"]["reportable"], "candidate_id"].tolist(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
