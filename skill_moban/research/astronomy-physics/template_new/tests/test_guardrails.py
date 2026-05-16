from __future__ import annotations

from pathlib import Path

import pandas as pd
from astropy.io import fits
from astropy.table import Table
from pandas.testing import assert_frame_equal

import reference_followup


def assert_required_outputs_present(answer_root: Path) -> None:
    actual_files = sorted(path.name for path in answer_root.iterdir() if path.is_file())
    assert actual_files == [
        "briefing.json",
        "candidate_followup_packet.ecsv",
        "host_association_audit.tsv",
        "photometry_context.tsv",
        "screening_diagnostics.tsv",
    ]


def test_input_data_remains_unchanged() -> None:
    assert reference_followup.current_data_hash(reference_followup.DATA_ROOT) == reference_followup.baseline_data_hash()


def test_output_inventory_is_exact() -> None:
    actual_files = sorted(path.name for path in reference_followup.ANSWER_ROOT.iterdir() if path.is_file())
    assert actual_files == [
        "briefing.json",
        "candidate_followup_packet.ecsv",
        "host_association_audit.tsv",
        "photometry_context.tsv",
        "screening_diagnostics.tsv",
    ]


def test_guardrail_science_image_mutation_changes_photometry() -> None:
    tmp_root = Path("/tmp/ngc4993_science_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    with fits.open(data_copy / "fits" / "ngc4993_g.fits", mode="update") as hdul:
        sci = hdul["SCI"].data
        sci[144:147, 157:160] += 180.0
        hdul.flush()

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    assert_required_outputs_present(answer_copy)
    actual = reference_followup.read_submission(answer_copy)["photometry_context"]
    original = reference_followup.read_submission()["photometry_context"].set_index("candidate_id")
    mutated = actual.set_index("candidate_id")
    assert mutated.loc["cand_medium_g", "flux_aperture"] != original.loc["cand_medium_g", "flux_aperture"]


def test_guardrail_wcs_header_mutation_changes_reconstruction() -> None:
    tmp_root = Path("/tmp/ngc4993_wcs_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    with fits.open(data_copy / "fits" / "ngc4993_z.fits", mode="update") as hdul:
        hdul["SCI"].header["CRVAL1"] = float(hdul["SCI"].header["CRVAL1"]) + 0.00025
        hdul.flush()

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    assert_required_outputs_present(answer_copy)
    actual = reference_followup.read_submission(answer_copy)["candidate_followup_packet"]
    original = reference_followup.read_submission()["candidate_followup_packet"].set_index("candidate_id")
    mutated = actual.set_index("candidate_id")
    assert mutated.loc["cand_large_z", "ra_deg"] != original.loc["cand_large_z", "ra_deg"]


def test_guardrail_proper_motion_mutation_changes_gaia_matching() -> None:
    tmp_root = Path("/tmp/ngc4993_pm_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    gaia_path = data_copy / "catalogs" / "gaia_foreground_slice.ecsv"
    gaia = Table.read(gaia_path, format="ascii.ecsv").to_pandas()
    mask = gaia["gaia_id"] == "gaia_fg_04"
    gaia.loc[mask, "pm_ra_cosdec_mas_per_yr"] = 0.0
    gaia.loc[mask, "pm_dec_mas_per_yr"] = 0.0
    Table.from_pandas(gaia).write(gaia_path, format="ascii.ecsv", overwrite=True)

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual_bundle = reference_followup.read_submission(answer_copy)
    assert_required_outputs_present(answer_copy)
    original_audit = reference_followup.read_submission()["host_association_audit"].set_index("candidate_id")
    mutated_audit = actual_bundle["host_association_audit"].set_index("candidate_id")
    original_diag = reference_followup.read_submission()["screening_diagnostics"].set_index("candidate_id")
    mutated_diag = actual_bundle["screening_diagnostics"].set_index("candidate_id")
    assert mutated_audit.loc["cand_star_g", "gaia_sep_arcsec"] != original_audit.loc["cand_star_g", "gaia_sep_arcsec"]
    assert (
        mutated_diag.loc["cand_star_g", "gaia_epoch_shift_arcsec"]
        != original_diag.loc["cand_star_g", "gaia_epoch_shift_arcsec"]
    )


def test_guardrail_host_redshift_mutation_changes_projected_offsets() -> None:
    tmp_root = Path("/tmp/ngc4993_redshift_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    props_path = data_copy / "catalogs" / "host_properties.fits"
    props = Table.read(props_path, format="fits").to_pandas()
    props["host_id"] = props["host_id"].map(lambda value: value.decode() if isinstance(value, bytes) else value)
    props.loc[props["host_id"] == "host_ngc4993", "redshift"] = 0.0135
    Table.from_pandas(props).write(props_path, format="fits", overwrite=True)

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    assert_required_outputs_present(answer_copy)
    actual = reference_followup.read_submission(answer_copy)["photometry_context"]
    original = reference_followup.read_submission()["photometry_context"].set_index("candidate_id")
    mutated = actual.set_index("candidate_id")
    assert mutated.loc["cand_large_z", "projected_offset_kpc"] != original.loc["cand_large_z", "projected_offset_kpc"]
    assert mutated.loc["cand_large_z", "luminosity_distance_mpc"] != original.loc["cand_large_z", "luminosity_distance_mpc"]


def test_guardrail_visit_metadata_mutation_changes_times_and_photometry() -> None:
    tmp_root = Path("/tmp/ngc4993_visit_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    visits = reference_followup.load_inputs(data_copy)["visits"]
    visits.loc[visits["visit_id"] == "visit_g", "obs_start_value"] = "2017-08-18T23:51:10"
    visits.loc[visits["visit_id"] == "visit_g", "exposure_seconds"] = 180.0
    visits.loc[visits["visit_id"] == "visit_g", "site_lon_deg"] = -70.1920
    visits.to_csv(data_copy / "observations" / "visit_manifest.tsv", sep="\t", index=False)

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual_bundle = reference_followup.read_submission(answer_copy)
    assert_required_outputs_present(answer_copy)
    original_packet = reference_followup.read_submission()["candidate_followup_packet"].set_index("candidate_id")
    mutated_packet = actual_bundle["candidate_followup_packet"].set_index("candidate_id")
    original_photo = reference_followup.read_submission()["photometry_context"].set_index("candidate_id")
    mutated_photo = actual_bundle["photometry_context"].set_index("candidate_id")
    assert mutated_packet.loc["cand_medium_g", "obs_time_bjd_tdb"] != original_packet.loc["cand_medium_g", "obs_time_bjd_tdb"]
    assert mutated_photo.loc["cand_medium_g", "altitude_deg"] != original_photo.loc["cand_medium_g", "altitude_deg"]


def test_guardrail_dq_mask_mutation_changes_measurement() -> None:
    tmp_root = Path("/tmp/ngc4993_dq_mutation")
    data_copy, pipeline_copy, answer_copy = reference_followup.copy_runtime_tree(tmp_root)

    with fits.open(data_copy / "fits" / "ngc4993_g.fits", mode="update") as hdul:
        dq = hdul["DQ"].data
        dq[111:113, 145:147] = 0
        hdul.flush()

    reference_followup.run_pipeline(pipeline_copy, data_copy, answer_copy)
    actual_bundle = reference_followup.read_submission(answer_copy)
    assert_required_outputs_present(answer_copy)
    original_photo = reference_followup.read_submission()["photometry_context"].set_index("candidate_id")
    mutated_photo = actual_bundle["photometry_context"].set_index("candidate_id")
    assert mutated_photo.loc["cand_uncertain_g", "flux_aperture"] != original_photo.loc["cand_uncertain_g", "flux_aperture"]
    assert mutated_photo.loc["cand_uncertain_g", "mag_unc"] != original_photo.loc["cand_uncertain_g", "mag_unc"]


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
