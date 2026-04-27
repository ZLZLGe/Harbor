#!/usr/bin/env python3
import argparse
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.table import Table


DATA = Path(os.environ.get("ENV_ROOT", "/root/environment")) / "data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/root/answer")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    detections = pd.read_csv(DATA / "detections" / "detections.csv")
    calibration = pd.read_csv(DATA / "calibration" / "filter_calibration.tsv", sep="\t").set_index("filter")

    astrometry_rows = []
    photometry_rows = []
    crossmatch_rows = []
    for det in detections.to_dict("records"):
        # Broken baseline: detector pixels are incorrectly treated as sky degrees,
        # exposure start times are ignored, and catalog matching is replaced by placeholders.
        filter_name = det["fits_file"].split("_")[2]
        cal = calibration.loc[filter_name]
        mag = float(cal["zeropoint_ab"]) - 2.5 * np.log10(float(det["flux_aperture"])) - float(cal["extinction_mag"])
        mag_unc = float(det["flux_err"]) / float(det["flux_aperture"])
        classification = "candidate" if det["snr"] >= 8 and det["quality_flags"] == "none" else "rejected"
        reportable = classification == "candidate"
        astrometry_rows.append(
            {
                "field_id": det["field_id"],
                "candidate_id": det["candidate_id"],
                "fits_file": det["fits_file"],
                "hdu_name": det["hdu_name"],
                "x_pixel": det["x_pixel"],
                "y_pixel": det["y_pixel"],
                "ra_icrs_deg": det["x_pixel"],
                "dec_icrs_deg": det["y_pixel"],
                "gal_l_deg": det["x_pixel"],
                "gal_b_deg": det["y_pixel"],
                "obstime_utc_iso": "2026-02-14T00:00:00.000",
                "obstime_mjd": 61085.0,
                "filter": filter_name,
                "snr": det["snr"],
                "quality_flags": det["quality_flags"],
                "classification": classification,
                "reportable": reportable,
            }
        )
        photometry_rows.append(
            {
                "candidate_id": det["candidate_id"],
                "flux_aperture": det["flux_aperture"],
                "flux_err": det["flux_err"],
                "zeropoint_ab": float(cal["zeropoint_ab"]),
                "extinction_mag": float(cal["extinction_mag"]),
                "calibrated_ab_mag": mag,
                "mag_unc": mag_unc,
                "host_id": "",
                "host_redshift": np.nan,
                "luminosity_distance_mpc": np.nan,
                "absolute_mag": np.nan,
            }
        )
        crossmatch_rows.append(
            {
                "candidate_id": det["candidate_id"],
                "nearest_gaia_source_id": "",
                "gaia_sep_arcsec": np.nan,
                "nearest_host_id": "",
                "host_sep_arcsec": np.nan,
                "nearest_moving_object_id": "",
                "moving_object_sep_arcsec": np.nan,
                "match_decision": "accepted" if reportable else "rejected",
                "rejection_reason": "baseline_placeholder",
            }
        )

    astrometry = pd.DataFrame(astrometry_rows)
    photometry = pd.DataFrame(photometry_rows)
    crossmatch = pd.DataFrame(crossmatch_rows)
    reportable_rows = astrometry[astrometry["reportable"]]
    report = {
        "n_input_detections": int(len(astrometry)),
        "n_reportable_candidates": int(len(reportable_rows)),
        "coordinate_frame": "unknown",
        "time_scale": "unknown",
        "cosmology": "not computed",
        "classification_summary": dict(Counter(astrometry["classification"])),
        "field_context_summary": {},
        "reportable_candidates": [
            {
                "candidate_id": row["candidate_id"],
                "ra_icrs_deg": row["ra_icrs_deg"],
                "dec_icrs_deg": row["dec_icrs_deg"],
                "obstime_utc_iso": row["obstime_utc_iso"],
                "calibrated_ab_mag": float(photometry.loc[photometry["candidate_id"] == row["candidate_id"], "calibrated_ab_mag"].iloc[0]),
                "classification": row["classification"],
                "primary_evidence": {},
            }
            for row in reportable_rows.to_dict("records")
        ],
        "notes": ["broken baseline output"],
    }

    Table.from_pandas(astrometry).write(out / "astrometric_candidates.ecsv", format="ascii.ecsv", overwrite=True)
    photometry.to_csv(out / "photometry_summary.tsv", sep="\t", index=False)
    crossmatch.to_csv(out / "crossmatch_audit.tsv", sep="\t", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "field_context.json").write_text("{}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
