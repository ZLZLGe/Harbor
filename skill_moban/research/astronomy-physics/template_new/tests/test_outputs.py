from __future__ import annotations

import pandas as pd
from pandas.testing import assert_frame_equal

import reference_followup


def assert_numeric_close(actual: pd.Series, expected: pd.Series, label: str, atol: float = 1e-6) -> None:
    actual_numeric = pd.to_numeric(actual, errors="coerce")
    expected_numeric = pd.to_numeric(expected, errors="coerce")
    delta = (actual_numeric - expected_numeric).abs()
    matches = delta.le(atol) | (actual_numeric.isna() & expected_numeric.isna())
    assert matches.all(), f"{label} max diff {delta.max()}"


def assert_priority_ranks_reasonable(frame: pd.DataFrame) -> None:
    ranks = pd.to_numeric(frame["priority_rank"], errors="coerce")
    assert ranks.notna().all(), "priority_rank must be numeric"
    assert (ranks % 1 == 0).all(), "priority_rank must be integer-like"
    assert ranks.between(1, len(frame)).all(), "priority_rank out of range"
    label_ranks = frame.groupby("screening_label")["priority_rank"].first().to_dict()
    assert label_ranks["high_priority_host_associated"] < label_ranks["medium_priority_host_associated"]
    for label, rank in label_ranks.items():
        if label not in {"high_priority_host_associated", "medium_priority_host_associated"}:
            assert label_ranks["medium_priority_host_associated"] < rank


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
    for column in [
        "x_pixel",
        "y_pixel",
        "ra_deg",
        "dec_deg",
        "gal_l_deg",
        "gal_b_deg",
        "obs_time_mjd",
        "snr",
    ]:
        assert_numeric_close(actual[column], expected[column], column)
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
        "flux_aperture",
        "flux_err",
        "zeropoint_ab",
        "extinction_mag",
        "exposure_seconds",
        "calibrated_mag",
        "mag_unc",
        "host_redshift",
        "luminosity_distance_mpc",
        "projected_offset_kpc",
    ]:
        assert_numeric_close(actual_photo[column], expected_photo[column], f"photometry {column}")

    expected_audit = reference_followup.sorted_frame(expected_bundle["host_association_audit"], ["candidate_id"])
    actual_audit = reference_followup.sorted_frame(actual_bundle["host_association_audit"], ["candidate_id"])
    assert_frame_equal(
        actual_audit[["candidate_id", "nearest_gaia_id", "nearest_host_id"]],
        expected_audit[["candidate_id", "nearest_gaia_id", "nearest_host_id"]],
        check_dtype=False,
    )
    assert_numeric_close(actual_audit["gaia_sep_arcsec"], expected_audit["gaia_sep_arcsec"], "gaia_sep_arcsec")
    assert_numeric_close(actual_audit["host_sep_arcsec"], expected_audit["host_sep_arcsec"], "host_sep_arcsec")

    expected_diag = reference_followup.sorted_frame(expected_bundle["screening_diagnostics"], ["candidate_id"])
    actual_diag = reference_followup.sorted_frame(actual_bundle["screening_diagnostics"], ["candidate_id"])
    for column in [
        "wcs_roundtrip_x_pixel",
        "wcs_roundtrip_y_pixel",
        "gaia_reject_margin_arcsec",
        "host_match_margin_arcsec",
        "screening_score",
    ]:
        assert_numeric_close(actual_diag[column], expected_diag[column], f"diagnostic {column}")


def test_briefing_matches_oracle_and_output_contract() -> None:
    expected = reference_followup.build_expected_bundle()["briefing"]
    actual = reference_followup.read_submission()["briefing"]
    assert actual["field_id"] == expected["field_id"] == "ngc4993_followup"
    assert actual["n_input_candidates"] == expected["n_input_candidates"] == 8
    assert actual["n_high_priority"] == expected["n_high_priority"] == 1
    assert actual["coordinate_frame"] == "ICRS"
    assert actual["time_scale"] == "UTC"
    assert actual["distance_model"] == expected["distance_model"]
    assert actual["screening_summary"] == expected["screening_summary"]
    assert reference_followup.normalize_briefing_candidates(actual["high_priority_candidates"]) == (
        reference_followup.normalize_briefing_candidates(expected["high_priority_candidates"])
    )
    assert isinstance(actual["notes"], list) and len(actual["notes"]) >= 2
