from __future__ import annotations

from common import (
    baseline_data_manifest,
    baseline_package_diff_hash,
    baseline_skill_manifest,
    current_data_manifest,
    current_package_diff_hash,
    current_skill_manifest,
)


def test_input_data_files_are_unchanged() -> None:
    assert current_data_manifest() == baseline_data_manifest()


def test_installed_skill_files_are_unchanged() -> None:
    assert current_skill_manifest() == baseline_skill_manifest()


def test_package_diff_stays_equal_to_the_candidate_baseline() -> None:
    assert current_package_diff_hash() == baseline_package_diff_hash()
