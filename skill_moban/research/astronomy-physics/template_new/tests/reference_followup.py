from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.cosmology import FlatLambdaCDM
from astropy.io import fits
from astropy.modeling import fitting, models
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.utils import iers
from astropy.wcs import WCS


iers.conf.auto_download = False
iers.conf.auto_max_age = None


DATA_ROOT = Path(os.environ.get("TASK_DATA_DIR", "/root/environment/data"))
PIPELINE_ROOT = Path(os.environ.get("TASK_PIPELINE_ROOT", "/root/environment/pipeline"))
ANSWER_ROOT = Path(os.environ.get("TASK_ANSWER_DIR", "/root/answer"))
BASELINE_HASH_PATH = Path(os.environ.get("TASK_BASELINE_HASH_PATH", "/opt/task-data.sha256"))

CANDIDATE_COLUMNS = [
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

AUDIT_COLUMNS = [
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

ALLOWED_LABELS = [
    "high_priority_host_associated",
    "medium_priority_host_associated",
    "review_large_host_offset",
    "review_uncertain_photometry",
    "review_no_host_match",
    "reject_low_snr",
    "reject_foreground_star",
    "reject_bad_measurement",
]

LABEL_PRIORITY = {label: index for index, label in enumerate(ALLOWED_LABELS, start=1)}


def load_inputs(data_root: Path = DATA_ROOT) -> dict[str, object]:
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


def resolve_host_coordinate(row: pd.Series) -> SkyCoord:
    frame = str(row["frame"]).strip().lower()
    unit_mode = str(row["unit_mode"]).strip().lower()
    if frame == "icrs" and unit_mode == "deg_deg":
        coord = SkyCoord(float(row["coord_1"]) * u.deg, float(row["coord_2"]) * u.deg, frame="icrs")
    elif unit_mode == "hourangle_deg":
        coord = SkyCoord(str(row["coord_1"]), str(row["coord_2"]), unit=(u.hourangle, u.deg), frame=frame)
    elif frame == "galactic" and unit_mode == "galactic_deg":
        coord = SkyCoord(l=float(row["coord_1"]) * u.deg, b=float(row["coord_2"]) * u.deg, frame="galactic")
    else:
        raise ValueError(f"unsupported host coordinate encoding: frame={frame}, unit_mode={unit_mode}")
    return coord.icrs


def build_host_catalog(host_coordinates: pd.DataFrame, host_properties: pd.DataFrame) -> pd.DataFrame:
    coords = host_coordinates.copy()
    positions = [resolve_host_coordinate(row) for _, row in coords.iterrows()]
    coords["ra_deg"] = [coord.ra.deg for coord in positions]
    coords["dec_deg"] = [coord.dec.deg for coord in positions]
    props = decode_bytes_frame(host_properties)
    return coords.merge(props, on="host_id", how="left")


def visit_location(visit: pd.Series) -> EarthLocation:
    return EarthLocation(
        lat=float(visit["site_lat_deg"]) * u.deg,
        lon=float(visit["site_lon_deg"]) * u.deg,
        height=float(visit["site_height_m"]) * u.m,
    )


def visit_midpoint(visit: pd.Series, location: EarthLocation) -> Time:
    start = Time(str(visit["obs_start_value"]), format=str(visit["time_format"]), scale=str(visit["time_scale"]), location=location)
    return start + TimeDelta(float(visit["exposure_seconds"]) / 2.0, format="sec")


def calibrated_mag(flux_aperture: float, exposure_seconds: float, zeropoint_ab: float, extinction_mag: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return zeropoint_ab - 2.5 * math.log10(flux_aperture / exposure_seconds) - extinction_mag


def magnitude_uncertainty(flux_aperture: float, flux_err: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return 1.0857362047581294 * flux_err / flux_aperture


def quality_flagged(flag_value: object) -> bool:
    if pd.isna(flag_value):
        return False
    return str(flag_value).strip().lower() not in {"", "none", "ok", "good", "clean"}


def refine_candidate_position(
    sci: np.ndarray,
    dq: np.ndarray,
    x_seed: float,
    y_seed: float,
    rules: dict[str, object],
) -> tuple[float, float]:
    half = int(rules["centroid_half_size_pix"])
    ix = int(round(x_seed)) - 1
    iy = int(round(y_seed)) - 1
    x_min = max(0, ix - half)
    x_max = min(sci.shape[1] - 1, ix + half)
    y_min = max(0, iy - half)
    y_max = min(sci.shape[0] - 1, iy + half)

    window = sci[y_min : y_max + 1, x_min : x_max + 1].copy()
    dq_window = dq[y_min : y_max + 1, x_min : x_max + 1]
    masked_window = window.copy()
    masked_window[dq_window != 0] = -np.inf
    peak_y, peak_x = np.unravel_index(np.nanargmax(masked_window), masked_window.shape)
    peak_x += x_min
    peak_y += y_min

    yy, xx = np.indices(sci.shape)
    xp = peak_x + 1.0
    yp = peak_y + 1.0
    radius = np.sqrt((xx + 1 - xp) ** 2 + (yy + 1 - yp) ** 2)
    annulus = (
        (radius >= float(rules["background_annulus_inner_pix"]))
        & (radius <= float(rules["background_annulus_outer_pix"]))
        & (dq == 0)
    )
    background_level = float(np.median(sci[annulus]))
    fit_data = window - background_level
    fit_data[dq_window != 0] = 0.0
    fit_good = dq_window == 0
    fit_x = (xx[y_min : y_max + 1, x_min : x_max + 1] + 1)[fit_good]
    fit_y = (yy[y_min : y_max + 1, x_min : x_max + 1] + 1)[fit_good]
    fit_values = fit_data[fit_good]

    if fit_values.size == 0 or float(np.nanmax(fit_values)) <= 0.0:
        return xp, yp

    gaussian = models.Gaussian2D(
        amplitude=float(max(np.nanmax(fit_values), 1.0)),
        x_mean=xp,
        y_mean=yp,
        x_stddev=1.4,
        y_stddev=1.4,
        bounds={
            "amplitude": (0.0, None),
            "x_mean": (max(1.0, xp - 2.5), min(float(sci.shape[1]), xp + 2.5)),
            "y_mean": (max(1.0, yp - 2.5), min(float(sci.shape[0]), yp + 2.5)),
            "x_stddev": (0.5, 4.0),
            "y_stddev": (0.5, 4.0),
        },
    )
    fitter = fitting.LevMarLSQFitter()
    fitted = fitter(gaussian, fit_x, fit_y, fit_values, maxiter=200)
    x_pixel = float(fitted.x_mean.value)
    y_pixel = float(fitted.y_mean.value)
    if not (math.isfinite(x_pixel) and math.isfinite(y_pixel)):
        return xp, yp
    return x_pixel, y_pixel


def measure_aperture_photometry(
    sci: np.ndarray,
    err: np.ndarray,
    dq: np.ndarray,
    x_pixel: float,
    y_pixel: float,
    rules: dict[str, object],
) -> tuple[float, float]:
    yy, xx = np.indices(sci.shape)
    radius = np.sqrt((xx + 1 - x_pixel) ** 2 + (yy + 1 - y_pixel) ** 2)
    aperture = (radius <= float(rules["aperture_radius_pix"])) & (dq == 0)
    annulus = (
        (radius >= float(rules["background_annulus_inner_pix"]))
        & (radius <= float(rules["background_annulus_outer_pix"]))
        & (dq == 0)
    )
    background_level = float(np.median(sci[annulus]))
    flux_aperture = float((sci[aperture] - background_level).sum())
    flux_err = float(np.sqrt((err[aperture] ** 2).sum()))
    return flux_aperture, flux_err


def screening_label_for_candidate(
    *,
    quality_flags: object,
    snr: float,
    gaia_sep_arcsec: float,
    host_sep_arcsec: float,
    mag_unc: float,
    projected_offset_kpc: float,
    rules: dict[str, object],
) -> tuple[str, str]:
    if quality_flagged(quality_flags):
        return "reject_bad_measurement", f"quality flags={quality_flags}"
    if math.isfinite(gaia_sep_arcsec) and gaia_sep_arcsec <= float(rules["gaia_reject_arcsec"]):
        return "reject_foreground_star", f"within Gaia reject radius ({gaia_sep_arcsec:.3f} arcsec)"
    if not math.isfinite(snr) or snr < float(rules["min_snr"]):
        return "reject_low_snr", f"SNR {snr:.2f} below minimum {float(rules['min_snr']):.2f}"
    if not math.isfinite(mag_unc) or mag_unc > float(rules["max_mag_unc"]):
        return "review_uncertain_photometry", f"magnitude uncertainty {mag_unc:.3f} exceeds {float(rules['max_mag_unc']):.3f}"
    if not math.isfinite(host_sep_arcsec) or host_sep_arcsec > float(rules["host_match_arcsec"]):
        return "review_no_host_match", f"nearest host separation {host_sep_arcsec:.3f} arcsec exceeds {float(rules['host_match_arcsec']):.3f}"
    if not math.isfinite(projected_offset_kpc) or projected_offset_kpc > float(rules["large_offset_kpc"]):
        return "review_large_host_offset", f"projected host offset {projected_offset_kpc:.3f} kpc exceeds {float(rules['large_offset_kpc']):.3f}"
    if (
        projected_offset_kpc <= float(rules["high_priority_offset_kpc"])
        and snr >= float(rules["high_priority_min_snr"])
    ):
        return "high_priority_host_associated", "matched host with compact offset and high SNR"
    return "medium_priority_host_associated", "matched host within review thresholds"


def screening_score_for_candidate(
    *,
    snr: float,
    projected_offset_kpc: float,
    mag_unc: float,
    screening_label: str,
    rules: dict[str, object],
) -> float:
    model = dict(rules["screening_score_model"])
    penalties = dict(model["label_penalties"])
    offset_term = projected_offset_kpc if math.isfinite(projected_offset_kpc) else 0.0
    mag_unc_term = mag_unc if math.isfinite(mag_unc) else float(rules["max_mag_unc"])
    return (
        float(model["snr_weight"]) * snr
        + float(model["projected_offset_kpc_weight"]) * offset_term
        + float(model["mag_unc_weight"]) * mag_unc_term
        - float(penalties.get(screening_label, 0.0))
    )


def build_expected_bundle(data_root: Path = DATA_ROOT) -> dict[str, object]:
    inputs = load_inputs(data_root)
    seeds = inputs["seeds"].copy()
    visits = inputs["visits"].copy()
    rules = dict(inputs["rules"])
    gaia_frame = inputs["gaia"].to_pandas()
    host_catalog = build_host_catalog(inputs["host_coordinates"], inputs["host_properties"])
    host_coords = SkyCoord(host_catalog["ra_deg"].to_numpy() * u.deg, host_catalog["dec_deg"].to_numpy() * u.deg, frame="icrs")
    cosmology = FlatLambdaCDM(
        H0=float(rules["distance_model"]["H0"]),
        Om0=float(rules["distance_model"]["Om0"]),
        Tcmb0=float(rules["distance_model"]["Tcmb0"]),
    )
    visit_map = visits.set_index("visit_id").to_dict("index")

    field_ids = seeds["field_id"].dropna().astype(str).unique().tolist()
    if len(field_ids) != 1:
        raise ValueError("Expected detections from exactly one field")

    packet_rows: list[dict[str, object]] = []
    photometry_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []

    gaia_raw_coords = SkyCoord(
        ra=gaia_frame["ra_deg"].to_numpy() * u.deg,
        dec=gaia_frame["dec_deg"].to_numpy() * u.deg,
        pm_ra_cosdec=gaia_frame["pm_ra_cosdec_mas_per_yr"].to_numpy() * u.mas / u.yr,
        pm_dec=gaia_frame["pm_dec_mas_per_yr"].to_numpy() * u.mas / u.yr,
        obstime=Time(gaia_frame["ref_epoch_jyear"].to_numpy(), format="jyear"),
        frame="icrs",
    )

    for seed in seeds.to_dict("records"):
        visit = pd.Series(visit_map[str(seed["visit_id"])])
        location = visit_location(visit)
        midpoint = visit_midpoint(visit, location)

        with fits.open(data_root / "fits" / str(seed["fits_file"])) as hdul:
            sci = hdul[str(rules["science_extname"])].data.astype(float)
            err = hdul[str(rules["error_extname"])].data.astype(float)
            dq = hdul[str(rules["dq_extname"])].data.astype(int)
            wcs = WCS(hdul[str(rules["science_extname"])].header)

        x_seed = float(seed["x_seed"])
        y_seed = float(seed["y_seed"])
        x_pixel, y_pixel = refine_candidate_position(sci, dq, x_seed, y_seed, rules)
        flux_aperture, flux_err = measure_aperture_photometry(sci, err, dq, x_pixel, y_pixel, rules)
        mag_unc = magnitude_uncertainty(flux_aperture, flux_err)
        calibrated = calibrated_mag(
            flux_aperture,
            float(visit["exposure_seconds"]),
            float(visit["zeropoint_ab"]),
            float(visit["extinction_mag"]),
        )

        sky_coord = SkyCoord.from_pixel(x_pixel, y_pixel, wcs, origin=1)
        galactic_coord = sky_coord.galactic
        roundtrip_x, roundtrip_y = sky_coord.to_pixel(wcs, origin=1)
        seed_offset_pix = math.hypot(x_pixel - x_seed, y_pixel - y_seed)

        gaia_visit_coords = gaia_raw_coords.apply_space_motion(new_obstime=midpoint.utc)
        gaia_index, gaia_sep, _ = sky_coord.match_to_catalog_sky(gaia_visit_coords)
        gaia_index = int(gaia_index)
        gaia_row = gaia_frame.iloc[gaia_index]
        gaia_sep_arcsec = float(np.asarray(gaia_sep.arcsec).item())
        gaia_epoch_shift_arcsec = float(gaia_raw_coords[gaia_index].separation(gaia_visit_coords[gaia_index]).arcsec)

        host_index, host_sep, _ = sky_coord.match_to_catalog_sky(host_coords)
        host_index = int(host_index)
        host_row = host_catalog.iloc[host_index]
        host_sep_arcsec = float(np.asarray(host_sep.arcsec).item())
        host_redshift = float(host_row["redshift"])
        luminosity_distance = cosmology.luminosity_distance(host_redshift)
        angular_diameter_distance = cosmology.angular_diameter_distance(host_redshift)
        projected_offset_kpc = float(
            sky_coord.separation(host_coords[host_index]).to(u.rad).value
            * angular_diameter_distance.to(u.kpc).value
        )

        barycentric_correction = midpoint.utc.light_travel_time(sky_coord, location=location, kind="barycentric")
        barycentric_time = midpoint.utc.tdb + barycentric_correction
        altaz = sky_coord.transform_to(AltAz(obstime=midpoint.utc, location=location))
        altitude_deg = float(altaz.alt.deg)
        airmass = float(altaz.secz.value) if np.isfinite(altaz.secz.value) else float("nan")

        screening_label, review_reason = screening_label_for_candidate(
            quality_flags=seed["quality_flags"],
            snr=float(seed["snr"]),
            gaia_sep_arcsec=gaia_sep_arcsec,
            host_sep_arcsec=host_sep_arcsec,
            mag_unc=mag_unc,
            projected_offset_kpc=projected_offset_kpc,
            rules=rules,
        )
        screening_score = screening_score_for_candidate(
            snr=float(seed["snr"]),
            projected_offset_kpc=projected_offset_kpc,
            mag_unc=mag_unc,
            screening_label=screening_label,
            rules=rules,
        )

        packet_rows.append(
            {
                "field_id": str(seed["field_id"]),
                "candidate_id": str(seed["candidate_id"]),
                "fits_file": str(seed["fits_file"]),
                "visit_id": str(seed["visit_id"]),
                "filter": str(seed["filter"]),
                "x_seed": x_seed,
                "y_seed": y_seed,
                "x_pixel": x_pixel,
                "y_pixel": y_pixel,
                "ra_deg": float(sky_coord.ra.deg),
                "dec_deg": float(sky_coord.dec.deg),
                "gal_l_deg": float(galactic_coord.l.deg),
                "gal_b_deg": float(galactic_coord.b.deg),
                "obs_time_iso": midpoint.utc.isot,
                "obs_time_mjd": float(midpoint.utc.mjd),
                "obs_time_bjd_tdb": float(barycentric_time.jd),
                "snr": float(seed["snr"]),
                "quality_flags": str(seed["quality_flags"]),
                "screening_label": screening_label,
                "priority_rank": 0,
            }
        )
        photometry_rows.append(
            {
                "candidate_id": str(seed["candidate_id"]),
                "flux_aperture": flux_aperture,
                "flux_err": flux_err,
                "zeropoint_ab": float(visit["zeropoint_ab"]),
                "extinction_mag": float(visit["extinction_mag"]),
                "exposure_seconds": float(visit["exposure_seconds"]),
                "calibrated_mag": calibrated,
                "mag_unc": mag_unc,
                "altitude_deg": altitude_deg,
                "airmass": airmass,
                "host_id": str(host_row["host_id"]),
                "host_redshift": host_redshift,
                "luminosity_distance_mpc": float(luminosity_distance.to(u.Mpc).value),
                "projected_offset_kpc": projected_offset_kpc,
            }
        )
        audit_rows.append(
            {
                "candidate_id": str(seed["candidate_id"]),
                "nearest_gaia_id": str(gaia_row["gaia_id"]),
                "gaia_reference_epoch_jyear": float(gaia_row["ref_epoch_jyear"]),
                "gaia_sep_arcsec": gaia_sep_arcsec,
                "nearest_host_id": str(host_row["host_id"]),
                "host_sep_arcsec": host_sep_arcsec,
                "host_match_status": (
                    "matched_within_radius"
                    if host_sep_arcsec <= float(rules["host_match_arcsec"])
                    else "outside_match_radius"
                ),
                "review_reason": review_reason,
            }
        )
        diagnostic_rows.append(
            {
                "candidate_id": str(seed["candidate_id"]),
                "seed_offset_pix": seed_offset_pix,
                "wcs_roundtrip_x_pixel": float(roundtrip_x),
                "wcs_roundtrip_y_pixel": float(roundtrip_y),
                "barycentric_correction_sec": float(barycentric_correction.to_value(u.s)),
                "gaia_epoch_shift_arcsec": gaia_epoch_shift_arcsec,
                "gaia_reject_margin_arcsec": gaia_sep_arcsec - float(rules["gaia_reject_arcsec"]),
                "host_match_margin_arcsec": float(rules["host_match_arcsec"]) - host_sep_arcsec,
                "screening_score": screening_score,
            }
        )

    candidate_followup_packet = pd.DataFrame(packet_rows, columns=CANDIDATE_COLUMNS)
    photometry_context = pd.DataFrame(photometry_rows, columns=PHOTOMETRY_COLUMNS)
    host_association_audit = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS)
    screening_diagnostics = pd.DataFrame(diagnostic_rows, columns=DIAGNOSTIC_COLUMNS)

    rank_frame = candidate_followup_packet.merge(
        screening_diagnostics[["candidate_id", "screening_score"]],
        on="candidate_id",
        how="left",
    )
    rank_frame["_tier"] = rank_frame["screening_label"].map(LABEL_PRIORITY)
    rank_frame = rank_frame.sort_values(
        by=["_tier", "screening_score", "candidate_id"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    rank_map = {candidate_id: rank for rank, candidate_id in enumerate(rank_frame["candidate_id"], start=1)}
    candidate_followup_packet["priority_rank"] = candidate_followup_packet["candidate_id"].map(rank_map).astype(int)

    merged = (
        candidate_followup_packet.merge(photometry_context, on="candidate_id", how="left")
        .sort_values(by=["priority_rank", "candidate_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    screening_summary = {
        label: int((candidate_followup_packet["screening_label"] == label).sum())
        for label in ALLOWED_LABELS
        if int((candidate_followup_packet["screening_label"] == label).sum()) > 0
    }
    high_priority_candidates = [
        {
            "candidate_id": row.candidate_id,
            "ra_deg": row.ra_deg,
            "dec_deg": row.dec_deg,
            "obs_time_iso": row.obs_time_iso,
            "obs_time_bjd_tdb": row.obs_time_bjd_tdb,
            "calibrated_mag": row.calibrated_mag,
            "screening_label": row.screening_label,
        }
        for row in merged.itertuples(index=False)
        if row.screening_label == "high_priority_host_associated"
    ]
    briefing = {
        "field_id": field_ids[0],
        "n_input_candidates": int(len(candidate_followup_packet)),
        "n_high_priority": int((candidate_followup_packet["screening_label"] == "high_priority_host_associated").sum()),
        "coordinate_frame": str(rules["coordinate_frame"]),
        "time_scale": str(rules["time_scale"]),
        "distance_model": rules["distance_model"],
        "screening_summary": screening_summary,
        "high_priority_candidates": high_priority_candidates,
        "notes": [
            "Candidate positions were refined from the FITS science image starting from 1-indexed detector seeds.",
            "Foreground-star matching used the bundled Gaia astrometric fields at each visit midpoint.",
            "Timing products include the UTC midpoint and the barycentric TDB correction from the bundled site metadata.",
            "Host distances and projected offsets were derived with the bundled FlatLambdaCDM parameter set.",
        ],
    }

    return {
        "candidate_followup_packet": candidate_followup_packet,
        "photometry_context": photometry_context,
        "host_association_audit": host_association_audit,
        "screening_diagnostics": screening_diagnostics,
        "briefing": briefing,
    }


def read_submission(answer_root: Path = ANSWER_ROOT) -> dict[str, object]:
    return {
        "candidate_followup_packet": Table.read(answer_root / "candidate_followup_packet.ecsv", format="ascii.ecsv").to_pandas(),
        "photometry_context": pd.read_csv(answer_root / "photometry_context.tsv", sep="\t"),
        "host_association_audit": pd.read_csv(answer_root / "host_association_audit.tsv", sep="\t"),
        "screening_diagnostics": pd.read_csv(answer_root / "screening_diagnostics.tsv", sep="\t"),
        "briefing": json.loads((answer_root / "briefing.json").read_text(encoding="utf-8")),
    }


def sorted_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    return frame.sort_values(columns).reset_index(drop=True)


def normalize_iso_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="raise").dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3]


def normalize_briefing_candidates(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in candidates:
        copy = dict(item)
        copy["obs_time_iso"] = normalize_iso_series(pd.Series([copy["obs_time_iso"]])).iloc[0]
        normalized.append(copy)
    return normalized


def run_pipeline(pipeline_root: Path, data_root: Path, answer_root: Path) -> None:
    answer_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(pipeline_root / "build_followup_packet.py"),
            "--data",
            str(data_root),
            "--output",
            str(answer_root),
        ],
        check=True,
        timeout=180,
    )


def current_data_hash(data_root: Path = DATA_ROOT) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(path for path in data_root.rglob("*") if path.is_file()):
        digest.update(str(file_path.relative_to(data_root)).encode("utf-8"))
        digest.update(hashlib.sha256(file_path.read_bytes()).hexdigest().encode("utf-8"))
    return digest.hexdigest()


def baseline_data_hash() -> str:
    if not BASELINE_HASH_PATH.exists():
        return current_data_hash()
    digest = hashlib.sha256()
    for line in BASELINE_HASH_PATH.read_text(encoding="utf-8").splitlines():
        file_hash, _, file_path = line.partition("  ")
        try:
            relative = str(Path(file_path).relative_to(DATA_ROOT))
        except ValueError:
            relative = str(Path(file_path).name)
        digest.update(relative.encode("utf-8"))
        digest.update(file_hash.encode("utf-8"))
    return digest.hexdigest()


def copy_runtime_tree(tmp_root: Path) -> tuple[Path, Path, Path]:
    data_copy = tmp_root / "data"
    pipeline_copy = tmp_root / "pipeline"
    answer_copy = tmp_root / "answer"
    shutil.rmtree(tmp_root, ignore_errors=True)
    shutil.copytree(DATA_ROOT, data_copy)
    shutil.copytree(PIPELINE_ROOT, pipeline_copy)
    return data_copy, pipeline_copy, answer_copy
