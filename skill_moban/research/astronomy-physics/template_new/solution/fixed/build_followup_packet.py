#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import astropy.units as u
import pandas as pd
from astropy.cosmology import FlatLambdaCDM
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.wcs import WCS


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


def midpoint_time(start_iso: str, exposure_seconds: float) -> tuple[str, float]:
    midpoint = Time(start_iso, scale="utc") + TimeDelta(exposure_seconds / 2.0, format="sec")
    return midpoint.to_value("isot"), float(midpoint.mjd)


def calibrated_mag(flux_aperture: float, exposure_seconds: float, zeropoint_ab: float, extinction_mag: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return zeropoint_ab - 2.5 * math.log10(flux_aperture / exposure_seconds) - extinction_mag


def magnitude_uncertainty(flux_aperture: float, flux_err: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return 1.0857362047581294 * flux_err / flux_aperture


def screening_score(label: str, snr: float, mag_unc: float, projected_offset_kpc: float) -> float:
    score = snr - projected_offset_kpc - (4.0 * mag_unc)
    penalties = {
        "reject_foreground_star": 10.0,
        "reject_low_snr": 8.0,
        "reject_bad_measurement": 12.0,
        "review_no_host_match": 6.0,
        "review_large_host_offset": 3.0,
        "review_uncertain_photometry": 3.5,
    }
    score -= penalties.get(label, 0.0)
    return float(score)


def classify_candidate(
    *,
    quality_flags: str,
    snr: float,
    gaia_sep_arcsec: float,
    host_sep_arcsec: float,
    mag_unc: float,
    projected_offset_kpc: float,
    rules: dict[str, object],
) -> str:
    if quality_flags != "none":
        return "reject_bad_measurement"
    if snr < float(rules["min_snr"]):
        return "reject_low_snr"
    if gaia_sep_arcsec <= float(rules["gaia_reject_arcsec"]):
        return "reject_foreground_star"
    if host_sep_arcsec > float(rules["host_match_arcsec"]):
        return "review_no_host_match"
    if not math.isfinite(mag_unc) or mag_unc > float(rules["max_mag_unc"]):
        return "review_uncertain_photometry"
    if projected_offset_kpc > float(rules["large_offset_kpc"]):
        return "review_large_host_offset"
    if (
        projected_offset_kpc <= float(rules["high_priority_offset_kpc"])
        and snr >= float(rules["high_priority_min_snr"])
    ):
        return "high_priority_host_associated"
    return "medium_priority_host_associated"


def load_inputs(data_root: Path) -> dict[str, object]:
    return {
        "detections": pd.read_csv(data_root / "detections" / "candidate_detections.csv"),
        "visits": pd.read_csv(data_root / "observations" / "visit_manifest.tsv", sep="\t"),
        "rules": json.loads((data_root / "observations" / "review_rules.json").read_text(encoding="utf-8")),
        "gaia": Table.read(data_root / "catalogs" / "gaia_foreground_slice.ecsv", format="ascii.ecsv"),
        "hosts": pd.read_csv(data_root / "catalogs" / "host_galaxies.tsv", sep="\t"),
    }


def flat_lcdm_distances_mpc(redshift: float, distance_model: dict[str, object]) -> tuple[float, float]:
    if redshift <= 0:
        return 0.0, 0.0

    cosmology = FlatLambdaCDM(
        H0=float(distance_model["H0"]),
        Om0=float(distance_model["Om0"]),
        Tcmb0=float(distance_model["Tcmb0"]),
    )
    luminosity_distance_mpc = float(cosmology.luminosity_distance(redshift).to_value("Mpc"))
    angular_diameter_distance_mpc = float(cosmology.angular_diameter_distance(redshift).to_value("Mpc"))
    return luminosity_distance_mpc, angular_diameter_distance_mpc


def build_bundle(data_root: Path) -> dict[str, object]:
    inputs = load_inputs(data_root)
    detections = inputs["detections"]
    visits = inputs["visits"]
    rules = inputs["rules"]
    gaia = inputs["gaia"]
    hosts = inputs["hosts"]

    visit_lookup = {row["visit_id"]: row for _, row in visits.iterrows()}
    wcs_lookup = {
        row["fits_file"]: WCS(fits.getheader(data_root / "fits" / row["fits_file"]))
        for _, row in visits.iterrows()
    }
    gaia_coords = SkyCoord(ra=gaia["ra_deg"] * u.deg, dec=gaia["dec_deg"] * u.deg, frame="icrs")
    host_coords = SkyCoord(
        ra=hosts["ra_deg"].to_numpy() * u.deg,
        dec=hosts["dec_deg"].to_numpy() * u.deg,
        frame="icrs",
    )

    candidate_rows: list[dict[str, object]] = []
    photometry_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []

    for _, detection in detections.iterrows():
        visit = visit_lookup[str(detection["visit_id"])]
        wcs = wcs_lookup[str(detection["fits_file"])]
        sky = SkyCoord.from_pixel(float(detection["x_pixel"]), float(detection["y_pixel"]), wcs, origin=1)
        galactic = sky.galactic
        obs_time_iso, obs_time_mjd = midpoint_time(str(visit["obs_start_utc"]), float(visit["exposure_seconds"]))

        gaia_seps = sky.separation(gaia_coords).arcsec
        gaia_index = int(gaia_seps.argmin())
        gaia_sep_arcsec = float(gaia_seps[gaia_index])
        nearest_gaia_id = str(gaia["gaia_id"][gaia_index])

        host_seps = sky.separation(host_coords).arcsec
        host_index = int(host_seps.argmin())
        host_sep_arcsec = float(host_seps[host_index])
        host_row = hosts.iloc[host_index]
        luminosity_distance_mpc, angular_diameter_distance_mpc = flat_lcdm_distances_mpc(
            float(host_row["redshift"]),
            rules["distance_model"],
        )
        projected_offset_kpc = float(
            math.radians(host_sep_arcsec / 3600.0) * angular_diameter_distance_mpc * 1000.0
        )

        flux_aperture = float(detection["flux_aperture"])
        flux_err = float(detection["flux_err"])
        zeropoint_ab = float(visit["zeropoint_ab"])
        extinction_mag = float(visit["extinction_mag"])
        exposure_seconds = float(visit["exposure_seconds"])
        mag = calibrated_mag(flux_aperture, exposure_seconds, zeropoint_ab, extinction_mag)
        mag_unc = magnitude_uncertainty(flux_aperture, flux_err)

        label = classify_candidate(
            quality_flags=str(detection["quality_flags"]),
            snr=float(detection["snr"]),
            gaia_sep_arcsec=gaia_sep_arcsec,
            host_sep_arcsec=host_sep_arcsec,
            mag_unc=mag_unc,
            projected_offset_kpc=projected_offset_kpc,
            rules=rules,
        )
        priority_rank = LABEL_PRIORITY[label]
        reason = "" if label.endswith("host_associated") else label
        host_match_status = (
            "foreground_overlap"
            if label == "reject_foreground_star"
            else "no_host_match"
            if label == "review_no_host_match"
            else "host_match"
        )

        candidate_rows.append(
            {
                "field_id": str(detection["field_id"]),
                "candidate_id": str(detection["candidate_id"]),
                "fits_file": str(detection["fits_file"]),
                "visit_id": str(detection["visit_id"]),
                "filter": str(detection["filter"]),
                "x_pixel": float(detection["x_pixel"]),
                "y_pixel": float(detection["y_pixel"]),
                "ra_deg": float(sky.ra.deg),
                "dec_deg": float(sky.dec.deg),
                "gal_l_deg": float(galactic.l.deg),
                "gal_b_deg": float(galactic.b.deg),
                "obs_time_iso": obs_time_iso,
                "obs_time_mjd": obs_time_mjd,
                "snr": float(detection["snr"]),
                "quality_flags": str(detection["quality_flags"]),
                "screening_label": label,
                "priority_rank": priority_rank,
            }
        )
        photometry_rows.append(
            {
                "candidate_id": str(detection["candidate_id"]),
                "flux_aperture": flux_aperture,
                "flux_err": flux_err,
                "zeropoint_ab": zeropoint_ab,
                "extinction_mag": extinction_mag,
                "exposure_seconds": exposure_seconds,
                "calibrated_mag": mag,
                "mag_unc": mag_unc,
                "host_id": str(host_row["host_id"]),
                "host_redshift": float(host_row["redshift"]),
                "luminosity_distance_mpc": luminosity_distance_mpc,
                "projected_offset_kpc": projected_offset_kpc,
            }
        )
        audit_rows.append(
            {
                "candidate_id": str(detection["candidate_id"]),
                "nearest_gaia_id": nearest_gaia_id,
                "gaia_sep_arcsec": gaia_sep_arcsec,
                "nearest_host_id": str(host_row["host_id"]),
                "host_sep_arcsec": host_sep_arcsec,
                "host_match_status": host_match_status,
                "review_reason": reason,
            }
        )
        roundtrip_x, roundtrip_y = sky.to_pixel(wcs, origin=1)
        diagnostic_rows.append(
            {
                "candidate_id": str(detection["candidate_id"]),
                "wcs_roundtrip_x_pixel": float(roundtrip_x),
                "wcs_roundtrip_y_pixel": float(roundtrip_y),
                "gaia_reject_margin_arcsec": gaia_sep_arcsec - float(rules["gaia_reject_arcsec"]),
                "host_match_margin_arcsec": float(rules["host_match_arcsec"]) - host_sep_arcsec,
                "screening_score": screening_score(label, float(detection["snr"]), mag_unc, projected_offset_kpc),
            }
        )

    candidate_df = pd.DataFrame(candidate_rows)
    photometry_df = pd.DataFrame(photometry_rows)
    audit_df = pd.DataFrame(audit_rows)
    diagnostic_df = pd.DataFrame(diagnostic_rows)

    summary = {
        label: int((candidate_df["screening_label"] == label).sum())
        for label in LABEL_PRIORITY
        if label in set(candidate_df["screening_label"])
    }
    photometry_lookup = photometry_df.set_index("candidate_id")
    high_priority_candidates = []
    for _, row in candidate_df[candidate_df["screening_label"] == "high_priority_host_associated"].iterrows():
        high_priority_candidates.append(
            {
                "candidate_id": row["candidate_id"],
                "ra_deg": float(row["ra_deg"]),
                "dec_deg": float(row["dec_deg"]),
                "obs_time_iso": row["obs_time_iso"],
                "calibrated_mag": float(photometry_lookup.loc[row["candidate_id"], "calibrated_mag"]),
                "screening_label": row["screening_label"],
            }
        )

    briefing = {
        "field_id": str(rules["field_id"]),
        "n_input_candidates": int(len(candidate_df)),
        "n_high_priority": int((candidate_df["screening_label"] == "high_priority_host_associated").sum()),
        "coordinate_frame": str(rules["coordinate_frame"]),
        "time_scale": str(rules["time_scale"]),
        "distance_model": rules["distance_model"],
        "screening_summary": summary,
        "high_priority_candidates": high_priority_candidates,
        "notes": [
            "Observation timestamps use the visit midpoint, not the visit start.",
            "Projected host offsets use the angular-diameter distance implied by the host redshift.",
        ],
    }

    return {
        "candidate_followup_packet": candidate_df,
        "photometry_context": photometry_df,
        "host_association_audit": audit_df,
        "screening_diagnostics": diagnostic_df,
        "briefing": briefing,
    }


def write_bundle(bundle: dict[str, object], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    Table.from_pandas(bundle["candidate_followup_packet"]).write(
        output_root / "candidate_followup_packet.ecsv",
        format="ascii.ecsv",
        overwrite=True,
    )
    bundle["photometry_context"].to_csv(output_root / "photometry_context.tsv", sep="\t", index=False)
    bundle["host_association_audit"].to_csv(output_root / "host_association_audit.tsv", sep="\t", index=False)
    bundle["screening_diagnostics"].to_csv(output_root / "screening_diagnostics.tsv", sep="\t", index=False)
    (output_root / "briefing.json").write_text(json.dumps(bundle["briefing"], indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    bundle = build_bundle(args.data)
    write_bundle(bundle, args.output)


if __name__ == "__main__":
    main()
