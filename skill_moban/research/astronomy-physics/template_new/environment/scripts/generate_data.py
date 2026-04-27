#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"


FIELDS = [
    {
        "field_id": "F01",
        "fits_file": "field_F01_r_20260214.fits",
        "filter": "r",
        "date_obs": "2026-02-14T06:12:00",
        "exptime": 120.0,
        "crval": (150.1132, 2.2055),
    },
    {
        "field_id": "F02",
        "fits_file": "field_F02_g_20260215.fits",
        "filter": "g",
        "date_obs": "2026-02-15T07:05:30",
        "exptime": 180.0,
        "crval": (149.8731, 2.4550),
    },
    {
        "field_id": "F03",
        "fits_file": "field_F03_i_20260216.fits",
        "filter": "i",
        "date_obs": "2026-02-16T05:48:15",
        "exptime": 90.0,
        "crval": (150.4210, 1.9250),
    },
]

DETECTIONS = [
    ("AT2026aa", "F01", 52.3, 48.9, 66000.0, 1200.0, 35.2, "none"),
    ("AT2026ab", "F01", 30.2, 75.4, 42000.0, 1800.0, 23.3, "none"),
    ("STAR-F01", "F01", 68.1, 25.8, 90000.0, 900.0, 60.0, "none"),
    ("MBO-F01", "F01", 43.5, 60.2, 50000.0, 1400.0, 31.1, "none"),
    ("LOW-SNR", "F02", 58.5, 51.1, 9000.0, 1800.0, 5.0, "none"),
    ("EDGE-F02", "F02", 5.2, 8.8, 30000.0, 1500.0, 20.0, "edge"),
    ("AT2026ac", "F02", 45.0, 42.0, 38000.0, 1100.0, 26.0, "none"),
    ("FAINT-F02", "F02", 77.7, 66.6, 7000.0, 500.0, 14.0, "none"),
    ("AT2026ad", "F03", 53.5, 52.1, 72000.0, 1300.0, 40.0, "none"),
    ("STAR-F03", "F03", 22.0, 30.0, 60000.0, 1000.0, 45.0, "none"),
    ("NOHOST-F03", "F03", 80.0, 20.0, 35000.0, 1100.0, 25.0, "none"),
    ("BADPHOT-F03", "F03", 40.0, 70.0, 10000.0, 4000.0, 12.0, "none"),
]

HOST_Z = {
    "AT2026aa": 0.080,
    "AT2026ab": 0.055,
    "STAR-F01": 0.070,
    "MBO-F01": 0.060,
    "LOW-SNR": 0.050,
    "EDGE-F02": 0.090,
    "AT2026ac": 0.120,
    "FAINT-F02": 0.020,
    "AT2026ad": 0.065,
    "STAR-F03": 0.040,
    "BADPHOT-F03": 0.100,
}


def make_wcs(field):
    scale = 0.4 / 3600.0
    w = WCS(naxis=2)
    w.wcs.crpix = [50.5, 50.5]
    w.wcs.crval = list(field["crval"])
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.cd = np.array([[-scale, 0.0], [0.0, scale]])
    return w


def offset_coord(coord, dra_arcsec, ddec_arcsec):
    return SkyCoord(
        ra=coord.ra + (dra_arcsec / np.cos(coord.dec.radian)) * u.arcsec,
        dec=coord.dec + ddec_arcsec * u.arcsec,
        frame="icrs",
    )


def main():
    rng = np.random.default_rng(20260426)
    for sub in ["fits", "detections", "catalogs", "calibration"]:
        (DATA / sub).mkdir(parents=True, exist_ok=True)

    field_by_id = {field["field_id"]: field for field in FIELDS}
    wcs_by_field = {}
    for field in FIELDS:
        w = make_wcs(field)
        wcs_by_field[field["field_id"]] = w
        image = rng.normal(loc=1000.0, scale=2.0, size=(100, 100)).astype("float32")
        hdr = w.to_header()
        hdr["FIELDID"] = field["field_id"]
        hdr["FILTER"] = field["filter"]
        hdr["DATE-OBS"] = field["date_obs"]
        hdr["EXPTIME"] = field["exptime"]
        primary = fits.PrimaryHDU()
        sci = fits.ImageHDU(image, header=hdr, name="SCI")
        fits.HDUList([primary, sci]).writeto(DATA / "fits" / field["fits_file"], overwrite=True)

    rows = []
    coords = {}
    for candidate_id, field_id, x, y, flux, flux_err, snr, flags in DETECTIONS:
        field = field_by_id[field_id]
        sky = wcs_by_field[field_id].pixel_to_world(x - 1, y - 1).icrs
        coords[candidate_id] = sky
        rows.append(
            {
                "field_id": field_id,
                "candidate_id": candidate_id,
                "fits_file": field["fits_file"],
                "hdu_name": "SCI",
                "x_pixel": x,
                "y_pixel": y,
                "flux_aperture": flux,
                "flux_err": flux_err,
                "snr": snr,
                "quality_flags": flags,
            }
        )
    pd.DataFrame(rows).to_csv(DATA / "detections" / "detections.csv", index=False)

    gaia_rows = [
        {
            "source_id": "Gaia-STAR-F01",
            "ra_icrs_deg": offset_coord(coords["STAR-F01"], 0.25, -0.10).ra.deg,
            "dec_icrs_deg": offset_coord(coords["STAR-F01"], 0.25, -0.10).dec.deg,
            "phot_g_mean_mag": 17.2,
        },
        {
            "source_id": "Gaia-STAR-F03",
            "ra_icrs_deg": offset_coord(coords["STAR-F03"], -0.15, 0.20).ra.deg,
            "dec_icrs_deg": offset_coord(coords["STAR-F03"], -0.15, 0.20).dec.deg,
            "phot_g_mean_mag": 18.4,
        },
        {
            "source_id": "Gaia-background-1",
            "ra_icrs_deg": coords["AT2026aa"].ra.deg + 0.015,
            "dec_icrs_deg": coords["AT2026aa"].dec.deg + 0.011,
            "phot_g_mean_mag": 20.1,
        },
        {
            "source_id": "Gaia-background-2",
            "ra_icrs_deg": coords["AT2026ac"].ra.deg - 0.020,
            "dec_icrs_deg": coords["AT2026ac"].dec.deg + 0.014,
            "phot_g_mean_mag": 19.8,
        },
    ]
    Table(rows=gaia_rows).write(DATA / "catalogs" / "gaia_reference.ecsv", format="ascii.ecsv", overwrite=True)

    host_rows = []
    for idx, (candidate_id, redshift) in enumerate(HOST_Z.items(), start=1):
        sky = offset_coord(coords[candidate_id], 2.0 + (idx % 3), -1.0 + (idx % 4) * 0.6)
        host_rows.append(
            {
                "host_id": f"HOST-{idx:03d}",
                "ra_icrs_deg": sky.ra.deg,
                "dec_icrs_deg": sky.dec.deg,
                "redshift": redshift,
                "host_label": f"review host {idx:03d}",
            }
        )
    host_rows.append(
        {
            "host_id": "HOST-FAR-NOHOST",
            "ra_icrs_deg": coords["NOHOST-F03"].ra.deg + 0.010,
            "dec_icrs_deg": coords["NOHOST-F03"].dec.deg + 0.010,
            "redshift": 0.075,
            "host_label": "too far for nohost candidate",
        }
    )
    pd.DataFrame(host_rows).to_csv(DATA / "catalogs" / "host_galaxies.tsv", sep="\t", index=False)

    mbo_mid = Time(field_by_id["F01"]["date_obs"], scale="utc") + field_by_id["F01"]["exptime"] * u.s / 2
    moving_coord = offset_coord(coords["MBO-F01"], -0.4, 0.25)
    pd.DataFrame(
        [
            {
                "object_id": "MPC-2026-A17",
                "ra_icrs_deg": moving_coord.ra.deg,
                "dec_icrs_deg": moving_coord.dec.deg,
                "valid_start_mjd": mbo_mid.mjd - 0.002,
                "valid_end_mjd": mbo_mid.mjd + 0.002,
            },
            {
                "object_id": "MPC-2026-Z99",
                "ra_icrs_deg": coords["AT2026ad"].ra.deg + 0.025,
                "dec_icrs_deg": coords["AT2026ad"].dec.deg - 0.020,
                "valid_start_mjd": Time("2026-02-20T00:00:00", scale="utc").mjd,
                "valid_end_mjd": Time("2026-02-21T00:00:00", scale="utc").mjd,
            },
        ]
    ).to_csv(DATA / "catalogs" / "moving_objects.tsv", sep="\t", index=False)

    pd.DataFrame(
        [
            {"filter": "g", "zeropoint_ab": 26.10, "extinction_mag": 0.09},
            {"filter": "r", "zeropoint_ab": 26.30, "extinction_mag": 0.07},
            {"filter": "i", "zeropoint_ab": 25.85, "extinction_mag": 0.05},
        ]
    ).to_csv(DATA / "calibration" / "filter_calibration.tsv", sep="\t", index=False)

    config = {
        "pixel_origin": 1,
        "time_reference": "mid_exposure_utc",
        "gaia_reject_arcsec": 1.5,
        "host_match_arcsec": 8.0,
        "moving_object_reject_arcsec": 3.0,
        "min_snr": 8.0,
        "max_mag_unc": 0.25,
        "reportable_absolute_mag_max": -16.0,
        "cosmology": "Planck18",
        "field_context_url": "http://127.0.0.1:8765/context",
    }
    (DATA / "calibration" / "triage_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
