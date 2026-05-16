#!/usr/bin/env python3
from __future__ import annotations

import math

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import Distance, EarthLocation, SkyCoord
from astropy.modeling import fitting, models
from astropy.time import Time, TimeDelta


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
    start = Time(
        str(visit["obs_start_value"]),
        format=str(visit["time_format"]),
        scale=str(visit["time_scale"]),
        location=location,
    )
    return start + TimeDelta(float(visit["exposure_seconds"]) / 2.0, format="sec")


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


def gaia_coordinates_at_time(gaia_frame: pd.DataFrame, midpoint: Time) -> tuple[SkyCoord, np.ndarray]:
    gaia = decode_bytes_frame(gaia_frame)
    gaia_raw_coords = SkyCoord(
        ra=gaia["ra_deg"].to_numpy() * u.deg,
        dec=gaia["dec_deg"].to_numpy() * u.deg,
        pm_ra_cosdec=gaia["pm_ra_cosdec_mas_per_yr"].to_numpy() * u.mas / u.yr,
        pm_dec=gaia["pm_dec_mas_per_yr"].to_numpy() * u.mas / u.yr,
        distance=Distance(parallax=gaia["parallax_mas"].to_numpy() * u.mas),
        obstime=Time(gaia["ref_epoch_jyear"].to_numpy(), format="jyear"),
        frame="icrs",
    )
    gaia_now = gaia_raw_coords.apply_space_motion(new_obstime=midpoint.tdb)
    gaia_shift_arcsec = gaia_raw_coords.separation(gaia_now).arcsec
    return gaia_now, np.asarray(gaia_shift_arcsec, dtype=float)
