from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

import reference_followup


def assert_candidate_packet_core_matches(actual: pd.DataFrame, expected: pd.DataFrame) -> None:
    actual = reference_followup.sorted_frame(actual, ["candidate_id"])
    expected = reference_followup.sorted_frame(expected, ["candidate_id"])
    assert_frame_equal(
        actual[["field_id", "candidate_id", "fits_file", "visit_id", "filter", "quality_flags", "screening_label"]],
        expected[["field_id", "candidate_id", "fits_file", "visit_id", "filter", "quality_flags", "screening_label"]],
        check_dtype=False,
    )
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
        actual_numeric = pd.to_numeric(actual[column], errors="coerce")
        expected_numeric = pd.to_numeric(expected[column], errors="coerce")
        delta = (actual_numeric - expected_numeric).abs()
        assert (delta <= 1e-6).all(), f"{column} max diff {delta.max()}"


def test_input_data_remains_unchanged() -> None:
    assert reference_followup.current_data_hash(reference_followup.DATA_ROOT) == reference_followup.baseline_data_hash()


def test_output_inventory_is_exact() -> None:
    actual_files = sorted(
        path.name
        for path in reference_followup.ANSWER_ROOT.iterdir()
        if path.is_file()
    )
    assert actual_files == [
        "briefing.json",
        "candidate_followup_packet.ecsv",
        "host_association_audit.tsv",
        "photometry_context.tsv",
        "screening_diagnostics.tsv",
    ]


def test_guardrail_candidate_position_mutation_changes_reconstruction() -> None:
    tmp_root = Path("/tmp/ngc4993_position_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    detections = reference_followup.load_inputs(data_copy)["detections"]
    mask = detections["candidate_id"] == "cand_large_z"
    detections.loc[mask, "x_pixel"] = float(detections.loc[mask, "x_pixel"].iloc[0]) + 12.0
    detections.to_csv(data_copy / "detections" / "candidate_detections.csv", index=False)

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual = reference_followup.read_submission(answer_copy)["candidate_followup_packet"]
    expected = reference_followup.build_expected_bundle(data_copy)["candidate_followup_packet"]
    assert_candidate_packet_core_matches(actual, expected)
    original = reference_followup.read_submission()["candidate_followup_packet"].set_index("candidate_id")
    mutated = actual.set_index("candidate_id")
    assert mutated.loc["cand_large_z", "ra_deg"] != original.loc["cand_large_z", "ra_deg"]


def test_guardrail_threshold_mutation_changes_labels() -> None:
    tmp_root = Path("/tmp/ngc4993_threshold_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    rules_path = data_copy / "observations" / "review_rules.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    rules["host_match_arcsec"] = 10.0
    rules["large_offset_kpc"] = 2.0
    rules_path.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual = reference_followup.read_submission(answer_copy)["candidate_followup_packet"]
    expected = reference_followup.build_expected_bundle(data_copy)["candidate_followup_packet"]
    assert_candidate_packet_core_matches(actual, expected)
    actual_labels = actual.set_index("candidate_id")["screening_label"].to_dict()
    assert actual_labels["cand_large_z"] == "review_no_host_match"


def test_guardrail_host_redshift_mutation_changes_projected_offsets() -> None:
    tmp_root = Path("/tmp/ngc4993_redshift_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    hosts = reference_followup.load_inputs(data_copy)["hosts"]
    hosts.loc[hosts["host_id"] == "host_ngc4993", "redshift"] = 0.0135
    hosts.to_csv(data_copy / "catalogs" / "host_galaxies.tsv", sep="\t", index=False)

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual = reference_followup.read_submission(answer_copy)["photometry_context"]
    expected = reference_followup.build_expected_bundle(data_copy)["photometry_context"]
    assert_frame_equal(
        reference_followup.sorted_frame(actual, ["candidate_id"]),
        reference_followup.sorted_frame(expected, ["candidate_id"]),
        check_dtype=False,
    )
    original = reference_followup.read_submission()["photometry_context"].set_index("candidate_id")
    mutated = actual.set_index("candidate_id")
    assert mutated.loc["cand_large_z", "projected_offset_kpc"] != original.loc["cand_large_z", "projected_offset_kpc"]


def test_guardrail_visit_metadata_mutation_changes_times_and_photometry() -> None:
    tmp_root = Path("/tmp/ngc4993_visit_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    visits = reference_followup.load_inputs(data_copy)["visits"]
    visits.loc[visits["visit_id"] == "visit_g", "obs_start_utc"] = "2017-08-18T23:51:10"
    visits.loc[visits["visit_id"] == "visit_g", "exposure_seconds"] = 180.0
    visits.to_csv(data_copy / "observations" / "visit_manifest.tsv", sep="\t", index=False)

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual_bundle = reference_followup.read_submission(answer_copy)
    expected_bundle = reference_followup.build_expected_bundle(data_copy)
    assert_candidate_packet_core_matches(
        actual_bundle["candidate_followup_packet"],
        expected_bundle["candidate_followup_packet"],
    )
    assert_frame_equal(
        reference_followup.sorted_frame(actual_bundle["photometry_context"], ["candidate_id"]),
        reference_followup.sorted_frame(expected_bundle["photometry_context"], ["candidate_id"]),
        check_dtype=False,
    )
    original_packet = reference_followup.read_submission()["candidate_followup_packet"].set_index("candidate_id")
    mutated_packet = actual_bundle["candidate_followup_packet"].set_index("candidate_id")
    assert mutated_packet.loc["cand_medium_g", "obs_time_iso"] != original_packet.loc["cand_medium_g", "obs_time_iso"]


def test_guardrail_repeated_run_is_deterministic() -> None:
    tmp_root = Path("/tmp/ngc4993_repeatability")
    data_copy, pipeline_copy, answer_a = reference_followup.copy_runtime_tree(tmp_root)
    answer_b = tmp_root / "answer_b"

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_a)
    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_b)

    for name in [
        "briefing.json",
        "candidate_followup_packet.ecsv",
        "host_association_audit.tsv",
        "photometry_context.tsv",
        "screening_diagnostics.tsv",
    ]:
        assert (answer_a / name).read_bytes() == (answer_b / name).read_bytes(), f"{name} is not deterministic"
