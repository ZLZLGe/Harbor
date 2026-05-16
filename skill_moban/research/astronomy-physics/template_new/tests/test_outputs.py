from __future__ import annotations

import pandas as pd
from pandas.testing import assert_frame_equal

import reference_followup


def assert_numeric_close(
    actual: pd.Series,
    expected: pd.Series,
    label: str,
    atol: float = 1e-6,
    rtol: float = 0.0,
) -> None:
    actual_numeric = pd.to_numeric(actual, errors="coerce")
    expected_numeric = pd.to_numeric(expected, errors="coerce")
    delta = (actual_numeric - expected_numeric).abs()
    tolerance = atol + rtol * expected_numeric.abs()
    matches = delta.le(tolerance) | (actual_numeric.isna() & expected_numeric.isna())
    assert matches.all(), f"{label} max diff {delta.max()}"


def assert_priority_ranks_reasonable(frame: pd.DataFrame) -> None:
    ranks = pd.to_numeric(frame["priority_rank"], errors="coerce")
    assert ranks.notna().all(), "priority_rank must be numeric"
    assert (ranks % 1 == 0).all(), "priority_rank must be integer-like"
    assert sorted(ranks.astype(int).tolist()) == list(range(1, len(frame) + 1))
    label_ranks = frame.groupby("screening_label")["priority_rank"].min().to_dict()
    assert label_ranks["high_priority_host_associated"] < label_ranks["medium_priority_host_associated"]


def test_required_outputs_exist_and_parse() -> None:
    required = [
        reference_followup.ANSWER_ROOT / "candidate_followup_packet.ecsv",
        reference_followup.ANSWER_ROOT / "photometry_context.tsv",
        reference_followup.ANSWER_ROOT / "host_association_audit.tsv",
        reference_followup.ANSWER_ROOT / "screening_diagnostics.tsv",
        reference_followup.ANSWER_ROOT / "briefing.json",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"
    outputs = reference_followup.read_submission()
    assert list(outputs["candidate_followup_packet"].columns) == reference_followup.CANDIDATE_COLUMNS
    assert list(outputs["photometry_context"].columns) == reference_followup.PHOTOMETRY_COLUMNS
    assert list(outputs["host_association_audit"].columns) == reference_followup.AUDIT_COLUMNS
    assert list(outputs["screening_diagnostics"].columns) == reference_followup.DIAGNOSTIC_COLUMNS


def test_candidate_packet_matches_oracle() -> None:
    expected = reference_followup.sorted_frame(
        reference_followup.build_expected_bundle()["candidate_followup_packet"],
        ["candidate_id"],
    )
    actual = reference_followup.sorted_frame(
        reference_followup.read_submission()["candidate_followup_packet"],
        ["candidate_id"],
    )
    assert_frame_equal(
        actual[["field_id", "candidate_id", "fits_file", "visit_id", "filter", "quality_flags", "screening_label"]],
        expected[["field_id", "candidate_id", "fits_file", "visit_id", "filter", "quality_flags", "screening_label"]],
        check_dtype=False,
    )
    assert_priority_ranks_reasonable(actual)
    assert list(reference_followup.normalize_iso_series(actual["obs_time_iso"])) == list(
        reference_followup.normalize_iso_series(expected["obs_time_iso"])
    )
    assert_numeric_close(actual["x_seed"], expected["x_seed"], "x_seed")
    assert_numeric_close(actual["y_seed"], expected["y_seed"], "y_seed")
    assert_numeric_close(actual["x_pixel"], expected["x_pixel"], "x_pixel", atol=0.35)
    assert_numeric_close(actual["y_pixel"], expected["y_pixel"], "y_pixel", atol=0.35)
    assert_numeric_close(actual["ra_deg"], expected["ra_deg"], "ra_deg", atol=5e-5)
    assert_numeric_close(actual["dec_deg"], expected["dec_deg"], "dec_deg", atol=5e-5)
    assert_numeric_close(actual["gal_l_deg"], expected["gal_l_deg"], "gal_l_deg", atol=5e-5)
    assert_numeric_close(actual["gal_b_deg"], expected["gal_b_deg"], "gal_b_deg", atol=5e-5)
    assert_numeric_close(actual["obs_time_mjd"], expected["obs_time_mjd"], "obs_time_mjd", atol=1e-9)
    assert_numeric_close(actual["obs_time_bjd_tdb"], expected["obs_time_bjd_tdb"], "obs_time_bjd_tdb", atol=5e-7)
    assert_numeric_close(actual["snr"], expected["snr"], "snr")
    assert set(actual["screening_label"]) == {
        "high_priority_host_associated",
        "medium_priority_host_associated",
        "review_uncertain_photometry",
        "review_large_host_offset",
        "review_no_host_match",
        "reject_low_snr",
        "reject_foreground_star",
        "reject_bad_measurement",
    }


def test_support_tables_match_oracle() -> None:
    expected_bundle = reference_followup.build_expected_bundle()
    actual_bundle = reference_followup.read_submission()

    expected_photo = reference_followup.sorted_frame(expected_bundle["photometry_context"], ["candidate_id"])
    actual_photo = reference_followup.sorted_frame(actual_bundle["photometry_context"], ["candidate_id"])
    assert_frame_equal(
        actual_photo[["candidate_id", "host_id"]],
        expected_photo[["candidate_id", "host_id"]],
        check_dtype=False,
    )
    for column in [
        "zeropoint_ab",
        "extinction_mag",
        "exposure_seconds",
        "altitude_deg",
        "airmass",
        "host_redshift",
        "luminosity_distance_mpc",
    ]:
        assert_numeric_close(actual_photo[column], expected_photo[column], f"photometry {column}")
    assert_numeric_close(actual_photo["flux_aperture"], expected_photo["flux_aperture"], "photometry flux_aperture", atol=100.0, rtol=0.15)
    assert_numeric_close(actual_photo["flux_err"], expected_photo["flux_err"], "photometry flux_err", atol=20.0, rtol=0.15)
    assert_numeric_close(actual_photo["calibrated_mag"], expected_photo["calibrated_mag"], "photometry calibrated_mag", atol=0.12)
    assert_numeric_close(actual_photo["mag_unc"], expected_photo["mag_unc"], "photometry mag_unc", atol=0.05)
    assert_numeric_close(actual_photo["projected_offset_kpc"], expected_photo["projected_offset_kpc"], "photometry projected_offset_kpc", atol=0.08)

    expected_audit = reference_followup.sorted_frame(expected_bundle["host_association_audit"], ["candidate_id"])
    actual_audit = reference_followup.sorted_frame(actual_bundle["host_association_audit"], ["candidate_id"])
    assert_frame_equal(
        actual_audit[["candidate_id", "nearest_gaia_id", "nearest_host_id"]],
        expected_audit[["candidate_id", "nearest_gaia_id", "nearest_host_id"]],
        check_dtype=False,
    )
    assert actual_audit["host_match_status"].fillna("").str.len().gt(0).all()
    assert actual_audit["review_reason"].fillna("").str.len().gt(0).all()
    assert_numeric_close(
        actual_audit["gaia_reference_epoch_jyear"],
        expected_audit["gaia_reference_epoch_jyear"],
        "gaia_reference_epoch_jyear",
    )
    assert_numeric_close(actual_audit["gaia_sep_arcsec"], expected_audit["gaia_sep_arcsec"], "gaia_sep_arcsec", atol=0.2)
    assert_numeric_close(actual_audit["host_sep_arcsec"], expected_audit["host_sep_arcsec"], "host_sep_arcsec", atol=0.2)

    actual_diag = reference_followup.sorted_frame(actual_bundle["screening_diagnostics"], ["candidate_id"])
    packet_by_id = actual_bundle["candidate_followup_packet"].set_index("candidate_id")
    photo_by_id = actual_bundle["photometry_context"].set_index("candidate_id")
    audit_by_id = actual_bundle["host_association_audit"].set_index("candidate_id")
    rules = reference_followup.load_inputs()["rules"]
    for row in actual_diag.to_dict("records"):
        candidate_id = row["candidate_id"]
        packet_row = packet_by_id.loc[candidate_id]
        photo_row = photo_by_id.loc[candidate_id]
        audit_row = audit_by_id.loc[candidate_id]
        expected_seed_offset = ((float(packet_row["x_pixel"]) - float(packet_row["x_seed"])) ** 2 + (float(packet_row["y_pixel"]) - float(packet_row["y_seed"])) ** 2) ** 0.5
        assert abs(float(row["seed_offset_pix"]) - expected_seed_offset) <= 1e-6
        assert abs(float(row["wcs_roundtrip_x_pixel"]) - float(packet_row["x_pixel"])) <= 1e-3
        assert abs(float(row["wcs_roundtrip_y_pixel"]) - float(packet_row["y_pixel"])) <= 1e-3
        assert abs(float(row["gaia_reject_margin_arcsec"]) - (float(audit_row["gaia_sep_arcsec"]) - float(rules["gaia_reject_arcsec"]))) <= 1e-6
        assert abs(float(row["host_match_margin_arcsec"]) - (float(rules["host_match_arcsec"]) - float(audit_row["host_sep_arcsec"]))) <= 1e-6
        expected_score = reference_followup.screening_score_for_candidate(
            snr=float(packet_row["snr"]),
            projected_offset_kpc=float(photo_row["projected_offset_kpc"]) if pd.notna(photo_row["projected_offset_kpc"]) else float("nan"),
            mag_unc=float(photo_row["mag_unc"]) if pd.notna(photo_row["mag_unc"]) else float("nan"),
            screening_label=str(packet_row["screening_label"]),
            rules=rules,
        )
        assert abs(float(row["screening_score"]) - expected_score) <= 1e-6
    expected_diag = reference_followup.sorted_frame(expected_bundle["screening_diagnostics"], ["candidate_id"])
    assert_numeric_close(actual_diag["barycentric_correction_sec"], expected_diag["barycentric_correction_sec"], "diagnostic barycentric_correction_sec", atol=1e-4)
    assert_numeric_close(actual_diag["gaia_epoch_shift_arcsec"], expected_diag["gaia_epoch_shift_arcsec"], "diagnostic gaia_epoch_shift_arcsec", atol=1e-4)


def test_briefing_matches_oracle_and_output_contract() -> None:
    expected = reference_followup.build_expected_bundle()["briefing"]
    actual = reference_followup.read_submission()["briefing"]
    packet = reference_followup.read_submission()["candidate_followup_packet"]
    photo = reference_followup.read_submission()["photometry_context"].set_index("candidate_id")
    assert actual["field_id"] == expected["field_id"] == "ngc4993_followup"
    assert actual["n_input_candidates"] == expected["n_input_candidates"] == 8
    assert actual["n_high_priority"] == expected["n_high_priority"] == 1
    assert actual["coordinate_frame"] == "ICRS"
    assert actual["time_scale"] == "UTC midpoint + BJD_TDB"
    assert actual["distance_model"] == expected["distance_model"]
    assert actual["screening_summary"] == expected["screening_summary"]
    expected_high_priority_ids = packet.loc[packet["screening_label"] == "high_priority_host_associated", "candidate_id"].tolist()
    actual_high_priority_ids = sorted(entry["candidate_id"] for entry in actual["high_priority_candidates"])
    assert sorted(expected_high_priority_ids) == actual_high_priority_ids
    for entry in actual["high_priority_candidates"]:
        row = packet.loc[packet["candidate_id"] == entry["candidate_id"]].iloc[0]
        assert entry["screening_label"] == row["screening_label"]
        assert entry["obs_time_iso"] == row["obs_time_iso"]
        assert abs(float(entry["obs_time_bjd_tdb"]) - float(row["obs_time_bjd_tdb"])) <= 5e-7
        assert abs(float(entry["ra_deg"]) - float(row["ra_deg"])) <= 5e-5
        assert abs(float(entry["dec_deg"]) - float(row["dec_deg"])) <= 5e-5
        assert abs(float(entry["calibrated_mag"]) - float(photo.loc[entry["candidate_id"], "calibrated_mag"])) <= 0.12
    assert isinstance(actual["notes"], list) and len(actual["notes"]) >= 3
