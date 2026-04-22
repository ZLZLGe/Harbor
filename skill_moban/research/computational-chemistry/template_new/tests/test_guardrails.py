from __future__ import annotations

from pathlib import Path

from conftest import (
    TASK_ROOT,
    assert_output_matches_reference_behavior,
    build_metadata_swapped_copy,
    build_shuffled_library_copy,
    build_solution_output,
    default_library_dir,
    reference_output,
)


def test_shuffled_input_order_and_filenames_do_not_change_behavior(reference_dir) -> None:
    shuffled_library = build_shuffled_library_copy(default_library_dir())
    expected = reference_output(shuffled_library, reference_dir)
    actual = build_solution_output(shuffled_library, reference_dir)
    assert_output_matches_reference_behavior(actual, expected)


def test_alternate_fixture_generalizes() -> None:
    alt_library = TASK_ROOT / "tests" / "fixtures_alt" / "library"
    alt_reference = TASK_ROOT / "tests" / "fixtures_alt" / "reference"
    expected = reference_output(alt_library, alt_reference, top_k=3)
    actual = build_solution_output(alt_library, alt_reference, top_k=3)

    assert_output_matches_reference_behavior(actual, expected)
    shortlist_ids = [row["compound_id"] for row in actual["shortlist"]]
    assert "ALT001_s_naproxen" in shortlist_ids
    assert "ALT002_s_naproxen_sodium" not in shortlist_ids
    assert actual["summary"]["n_standardized_candidates"] == 7


def test_result_follows_structure_not_metadata_names(reference_dir) -> None:
    swapped_library = build_metadata_swapped_copy(default_library_dir())
    baseline = build_solution_output(default_library_dir(), reference_dir)
    actual = build_solution_output(swapped_library, reference_dir)
    assert_output_matches_reference_behavior(actual, baseline)


def test_no_trivial_all_keep_or_all_reject_output() -> None:
    output = build_solution_output()
    assert output["summary"]["n_keep"] > 0
    assert output["summary"]["n_reject"] > 0
    assert len(output["shortlist"]) == output["summary"]["n_keep"]
    assert len(output["rejected_compounds"]) == output["summary"]["n_reject"]

    all_ids = {row["compound_id"] for row in output["shortlist"]}
    rejected_ids = {row["compound_id"] for row in output["rejected_compounds"]}
    assert all_ids.isdisjoint(rejected_ids)
