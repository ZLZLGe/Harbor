import json
import hashlib
import os
import subprocess
import sys
from collections import Counter
from functools import lru_cache
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


OUTPUT = Path(os.environ.get("ANSWER_DIR", "/root/answer"))
ENV_ROOT = Path(os.environ.get("ENV_ROOT", "/root/environment"))
DATA = ENV_ROOT / "data"
PIPELINE = ENV_ROOT / "pipeline" / "run_transient_triage.py"

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


def _read_astrometry() -> pd.DataFrame:
    table = Table.read(OUTPUT / "astrometric_candidates.ecsv", format="ascii.ecsv")
    frame = table.to_pandas()
    if frame["reportable"].dtype != bool:
        frame["reportable"] = frame["reportable"].map(lambda value: str(value).lower() == "true")
    return frame


def _nearest(coord: SkyCoord, catalog: pd.DataFrame, id_column: str):
    if catalog.empty:
        return "", float("nan"), None
    coords = SkyCoord(catalog["ra_icrs_deg"].to_numpy(float) * u.deg, catalog["dec_icrs_deg"].to_numpy(float) * u.deg)
    separations = coord.separation(coords)
    idx = int(np.argmin(separations.arcsec))
    row = catalog.iloc[idx]
    return str(row[id_column]), float(separations[idx].arcsec), row


def _classify(row: dict, cfg: dict):
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


def _row_signature(candidate_id, sky, classification, reportable, mag, gaia_id, host_id_raw, moving_id):
    body = (
        f"{SIGNATURE_DOMAIN}|{candidate_id}|{sky.ra.deg:.7f}|{sky.dec.deg:.7f}|{classification}|"
        f"{int(bool(reportable))}|{mag:.6f}|{gaia_id}|{host_id_raw}|{moving_id}"
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def reference() -> dict:
    cfg = json.loads((DATA / "calibration" / "triage_config.json").read_text(encoding="utf-8"))
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
            wcs = WCS(hdu.header)
            sky = wcs.pixel_to_world(det["x_pixel"] - cfg["pixel_origin"], det["y_pixel"] - cfg["pixel_origin"]).icrs
            roundtrip_x, roundtrip_y = wcs.world_to_pixel(sky)
            roundtrip_x += cfg["pixel_origin"]
            roundtrip_y += cfg["pixel_origin"]
            gal = sky.galactic
            obstime = Time(hdu.header["DATE-OBS"], scale="utc") + float(hdu.header["EXPTIME"]) * u.s / 2
            exposure = float(hdu.header["EXPTIME"])
            filter_name = str(hdu.header["FILTER"])

        gaia_id, gaia_sep, _ = _nearest(sky, gaia, "source_id")
        host_id_raw, host_sep, host_row = _nearest(sky, hosts, "host_id")
        host_id = host_id_raw if host_sep <= cfg["host_match_arcsec"] else ""
        host_redshift = float(host_row["redshift"]) if host_id else float("nan")

        moving_valid = moving[(moving["valid_start_mjd"] <= obstime.mjd) & (moving["valid_end_mjd"] >= obstime.mjd)]
        moving_id, moving_sep, _ = _nearest(sky, moving_valid, "object_id")

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

        classification, reportable, rejection = _classify(
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
                "row_signature": _row_signature(
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

    return {
        "astrometry": pd.DataFrame(astrometry_rows),
        "photometry": pd.DataFrame(photometry_rows),
        "crossmatch": pd.DataFrame(crossmatch_rows),
        "diagnostics": pd.DataFrame(diagnostic_rows),
        "reportable_payload": sorted(reportable_payload, key=lambda item: item["candidate_id"]),
        "cfg": cfg,
    }


def setup_module(module):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(PIPELINE), "--output", str(OUTPUT)], check=True, timeout=120)


def test_required_outputs_exist_and_parse():
    for filename in [
        "astrometric_candidates.ecsv",
        "photometry_summary.tsv",
        "crossmatch_audit.tsv",
        "triage_diagnostics.tsv",
        "report.json",
        "field_context.json",
    ]:
        assert (OUTPUT / filename).exists(), filename

    astrometry = _read_astrometry()
    photometry = pd.read_csv(OUTPUT / "photometry_summary.tsv", sep="\t")
    crossmatch = pd.read_csv(OUTPUT / "crossmatch_audit.tsv", sep="\t")
    diagnostics = pd.read_csv(OUTPUT / "triage_diagnostics.tsv", sep="\t")
    report = json.loads((OUTPUT / "report.json").read_text(encoding="utf-8"))
    field_context = json.loads((OUTPUT / "field_context.json").read_text(encoding="utf-8"))

    detections = pd.read_csv(DATA / "detections" / "detections.csv")
    assert list(astrometry.columns) == ASTROMETRY_COLUMNS
    assert list(photometry.columns) == PHOTOMETRY_COLUMNS
    assert list(crossmatch.columns) == CROSSMATCH_COLUMNS
    assert list(diagnostics.columns) == DIAGNOSTIC_COLUMNS
    assert len(astrometry) == len(detections) == len(photometry) == len(crossmatch) == len(diagnostics)
    assert astrometry["candidate_id"].is_unique
    assert set(astrometry["candidate_id"]) == set(detections["candidate_id"])
    assert set(report) == {
        "n_input_detections",
        "n_reportable_candidates",
        "coordinate_frame",
        "time_scale",
        "cosmology",
        "classification_summary",
        "field_context_summary",
        "reportable_candidates",
        "notes",
    }
    assert field_context == report["field_context_summary"]


def test_diagnostic_ledger_matches_astropy_reconstruction():
    expected = reference()["diagnostics"].set_index("candidate_id")
    actual = pd.read_csv(OUTPUT / "triage_diagnostics.tsv", sep="\t").replace({np.nan: ""}).set_index("candidate_id")

    assert set(actual.index) == set(expected.index)
    for candidate_id, row in expected.iterrows():
        got = actual.loc[candidate_id]
        for column in [
            "wcs_roundtrip_x_pixel",
            "wcs_roundtrip_y_pixel",
            "gaia_reject_margin_arcsec",
            "host_match_margin_arcsec",
        ]:
            assert abs(float(got[column]) - row[column]) < 2e-6
        if np.isfinite(row["moving_object_reject_margin_arcsec"]):
            assert abs(float(got["moving_object_reject_margin_arcsec"]) - row["moving_object_reject_margin_arcsec"]) < 2e-6
        else:
            assert str(got["moving_object_reject_margin_arcsec"]) == ""
        assert int(got["classification_priority"]) == int(row["classification_priority"])
        assert str(got["row_signature"]) == row["row_signature"]


def test_astrometry_and_time_match_fits_wcs_reference():
    expected = reference()["astrometry"].set_index("candidate_id")
    actual = _read_astrometry().set_index("candidate_id")

    for candidate_id, row in expected.iterrows():
        got = actual.loc[candidate_id]
        assert got["field_id"] == row["field_id"]
        assert got["fits_file"] == row["fits_file"]
        assert got["hdu_name"] == row["hdu_name"]
        assert abs(float(got["ra_icrs_deg"]) - row["ra_icrs_deg"]) < 2e-7
        assert abs(float(got["dec_icrs_deg"]) - row["dec_icrs_deg"]) < 2e-7
        assert abs(float(got["gal_l_deg"]) - row["gal_l_deg"]) < 2e-7
        assert abs(float(got["gal_b_deg"]) - row["gal_b_deg"]) < 2e-7
        assert got["obstime_utc_iso"] == row["obstime_utc_iso"]
        assert abs(float(got["obstime_mjd"]) - row["obstime_mjd"]) < 1e-10

    assert actual["ra_icrs_deg"].between(149.8, 150.5).all()
    assert actual["dec_icrs_deg"].between(1.8, 2.6).all()


def test_crossmatch_and_classification_decisions_are_consistent():
    expected_astrometry = reference()["astrometry"].set_index("candidate_id")
    expected_crossmatch = reference()["crossmatch"].set_index("candidate_id")
    actual_astrometry = _read_astrometry().set_index("candidate_id")
    actual_crossmatch = pd.read_csv(OUTPUT / "crossmatch_audit.tsv", sep="\t").fillna("").set_index("candidate_id")

    assert set(actual_astrometry["classification"]) == {
        "extragalactic_transient",
        "reject_stellar_counterpart",
        "reject_moving_object",
        "reject_low_snr",
        "reject_quality_flag",
        "review_faint_host_association",
        "review_no_host",
        "reject_uncertain_photometry",
    }
    assert set(actual_astrometry.index[actual_astrometry["reportable"]]) == set(
        expected_astrometry.index[expected_astrometry["reportable"]]
    )

    for candidate_id, row in expected_crossmatch.iterrows():
        got = actual_crossmatch.loc[candidate_id]
        assert got["nearest_gaia_source_id"] == row["nearest_gaia_source_id"]
        assert abs(float(got["gaia_sep_arcsec"]) - row["gaia_sep_arcsec"]) < 2e-4
        assert got["nearest_host_id"] == row["nearest_host_id"]
        assert abs(float(got["host_sep_arcsec"]) - row["host_sep_arcsec"]) < 2e-4
        assert got["nearest_moving_object_id"] == row["nearest_moving_object_id"]
        if np.isfinite(row["moving_object_sep_arcsec"]):
            assert abs(float(got["moving_object_sep_arcsec"]) - row["moving_object_sep_arcsec"]) < 2e-4
        expected_classification = expected_astrometry.loc[candidate_id, "classification"]
        actual_classification = actual_astrometry.loc[candidate_id, "classification"]
        assert actual_classification == expected_classification

        decision_text = str(got["match_decision"]).lower()
        reason_text = str(got["rejection_reason"]).lower()
        if bool(expected_astrometry.loc[candidate_id, "reportable"]):
            assert "reject" not in decision_text and "fail" not in decision_text
        else:
            assert decision_text not in {"accepted", "reportable", "extragalactic_transient"}
            assert reason_text
            assert reason_text in {
                str(row["rejection_reason"]).lower(),
                expected_classification.lower(),
            }


def test_photometry_and_cosmology_values_match_reference():
    expected = reference()["photometry"].set_index("candidate_id")
    actual = pd.read_csv(OUTPUT / "photometry_summary.tsv", sep="\t").replace({np.nan: ""}).set_index("candidate_id")

    for candidate_id, row in expected.iterrows():
        got = actual.loc[candidate_id]
        for column in [
            "flux_aperture",
            "flux_err",
            "zeropoint_ab",
            "extinction_mag",
            "calibrated_ab_mag",
            "mag_unc",
        ]:
            assert abs(float(got[column]) - row[column]) < 1e-7
        assert str(got["host_id"]) == (row["host_id"] if row["host_id"] else "")
        for column in ["host_redshift", "luminosity_distance_mpc", "absolute_mag"]:
            if np.isfinite(row[column]):
                assert abs(float(got[column]) - row[column]) < 1e-6
            else:
                assert str(got[column]) == ""


def test_report_and_field_context_match_generated_tables():
    astrometry = _read_astrometry()
    photometry = pd.read_csv(OUTPUT / "photometry_summary.tsv", sep="\t")
    report = json.loads((OUTPUT / "report.json").read_text(encoding="utf-8"))
    field_context = json.loads((OUTPUT / "field_context.json").read_text(encoding="utf-8"))
    expected = reference()

    assert report["n_input_detections"] == len(astrometry)
    assert report["n_reportable_candidates"] == int(astrometry["reportable"].sum())
    coordinate_frame_text = json.dumps(report["coordinate_frame"], sort_keys=True)
    time_scale_text = json.dumps(report["time_scale"], sort_keys=True)
    cosmology_text = json.dumps(report["cosmology"], sort_keys=True)
    assert "ICRS" in coordinate_frame_text
    assert "UTC" in time_scale_text and "MJD" in time_scale_text
    assert "Planck18" in cosmology_text
    assert report["classification_summary"] == dict(sorted(Counter(astrometry["classification"]).items()))

    reported_ids = [item["candidate_id"] for item in report["reportable_candidates"]]
    expected_ids = [item["candidate_id"] for item in expected["reportable_payload"]]
    assert reported_ids == expected_ids
    for item in report["reportable_candidates"]:
        ast_row = astrometry.set_index("candidate_id").loc[item["candidate_id"]]
        phot_row = photometry.set_index("candidate_id").loc[item["candidate_id"]]
        assert abs(float(item["ra_icrs_deg"]) - float(ast_row["ra_icrs_deg"])) < 2e-7
        assert abs(float(item["dec_icrs_deg"]) - float(ast_row["dec_icrs_deg"])) < 2e-7
        assert item["obstime_utc_iso"] == ast_row["obstime_utc_iso"]
        assert abs(float(item["calibrated_ab_mag"]) - float(phot_row["calibrated_ab_mag"])) < 1e-7
        assert item["classification"] == "extragalactic_transient"
        assert isinstance(item["primary_evidence"], dict) and item["primary_evidence"]
        evidence_keys = {str(key).lower() for key in item["primary_evidence"]}
        assert any("host" in key for key in evidence_keys)
        assert any("mag" in key or "snr" in key for key in evidence_keys)

    response = requests.post(
        reference()["cfg"]["field_context_url"],
        json={"candidates": expected["reportable_payload"]},
        timeout=10,
    )
    response.raise_for_status()
    assert field_context == response.json()
    assert field_context["service"] == "field-context"
    assert field_context["n_candidates"] == report["n_reportable_candidates"]


def test_guardrails_reject_pixel_coordinate_and_placeholder_outputs():
    astrometry = _read_astrometry()
    crossmatch = pd.read_csv(OUTPUT / "crossmatch_audit.tsv", sep="\t")
    report = json.loads((OUTPUT / "report.json").read_text(encoding="utf-8"))

    assert not np.allclose(astrometry["ra_icrs_deg"], astrometry["x_pixel"])
    assert not np.allclose(astrometry["dec_icrs_deg"], astrometry["y_pixel"])
    assert crossmatch["nearest_gaia_source_id"].astype(str).str.len().gt(0).any()
    assert crossmatch["nearest_host_id"].astype(str).str.len().gt(0).any()
    assert (crossmatch["gaia_sep_arcsec"].astype(float) < 1.5).any()
    assert (crossmatch["moving_object_sep_arcsec"].astype(float) < 3.0).any()
    assert report["field_context_summary"] != {}
    assert set(astrometry.loc[astrometry["reportable"], "candidate_id"]) == {
        "AT2026aa",
        "AT2026ab",
        "AT2026ac",
        "AT2026ad",
    }
