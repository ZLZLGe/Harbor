from __future__ import annotations

import json
import os
from pathlib import Path


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
REPORT_PATH = APP_DIR / "build_boundary_report.json"
REPO_PATH = APP_DIR / "packaging_backend_repo"


def _load_report() -> dict:
    assert REPORT_PATH.exists(), "build_boundary_report.json does not exist."
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert len(text.strip()) > 1500, "build_boundary_report.json is too short to be a real analysis."
    data = json.loads(text)
    assert isinstance(data, dict), "build_boundary_report.json must contain a JSON object."
    return data


def _candidate_map(data: dict) -> dict[str, dict]:
    candidates = data.get("boundary_candidates")
    assert isinstance(candidates, list) and len(candidates) >= 4, "boundary_candidates must contain at least 4 entries."
    return {entry["qualname"]: entry for entry in candidates}


def test_repository_assets_exist() -> None:
    assert REPO_PATH.exists(), "packaging_backend_repo is missing."
    for rel_path in [
        "packager_backend/config.py",
        "packager_backend/metadata.py",
        "packager_backend/build_backend.py",
        "tests/test_backend.py",
    ]:
        assert (REPO_PATH / rel_path).exists(), f"Missing fixture file: {rel_path}"


def test_report_has_required_top_level_sections() -> None:
    data = _load_report()
    for key in ["repo_focus", "important_files", "boundary_candidates", "existing_tests", "top_priorities"]:
        assert key in data, f"Missing top-level field: {key}"

    important_files = data["important_files"]
    assert isinstance(important_files, list) and len(important_files) >= 3, "important_files must contain at least 3 entries."
    for item in important_files:
        assert set(["path", "priority", "reason"]).issubset(item), "Each important_files entry needs path/priority/reason."


def test_report_mentions_expected_functions_and_failures() -> None:
    data = _load_report()
    candidates = _candidate_map(data)

    required = [
        "packager_backend.build_backend.collect_build_request",
        "packager_backend.config.normalize_config_settings",
        "packager_backend.config.load_pyproject",
        "packager_backend.metadata.normalize_entry_points",
    ]
    for qualname in required:
        assert qualname in candidates, f"Missing expected boundary candidate: {qualname}"

    collect_request = candidates["packager_backend.build_backend.collect_build_request"]
    assert collect_request["priority"] == 1, "collect_build_request should be the highest-priority boundary."
    assert "pyproject.toml" in " ".join(collect_request["inputs"])
    assert any("editable" in item.lower() for item in collect_request["failure_modes"])
    assert any("tests/test_backend.py" in ref for ref in collect_request["existing_test_refs"])

    normalize_config = candidates["packager_backend.config.normalize_config_settings"]
    assert any("config_settings" in item for item in normalize_config["why_it_matters"].split()), "normalize_config_settings reasoning should mention config_settings."
    assert any("requested-targets" in probe for probe in normalize_config["suggested_probes"])

    load_pyproject = candidates["packager_backend.config.load_pyproject"]
    assert any("TOML" in mode or "toml" in mode for mode in load_pyproject["failure_modes"])

    normalize_entry_points = candidates["packager_backend.metadata.normalize_entry_points"]
    assert normalize_entry_points["build_stage"] == "metadata-normalization"
    assert any("entry-point" in mode for mode in normalize_entry_points["failure_modes"])


def test_report_summarizes_existing_tests_and_gaps() -> None:
    data = _load_report()
    tests_section = data["existing_tests"]
    assert isinstance(tests_section, dict), "existing_tests must be an object."

    covered = tests_section.get("covered_paths")
    gaps = tests_section.get("gaps")
    assert isinstance(covered, list) and len(covered) >= 3, "covered_paths must summarize multiple test files."
    assert isinstance(gaps, list) and len(gaps) >= 3, "gaps must identify multiple missing edge cases."

    joined_covered = " ".join(covered)
    for needle in ["tests/test_config.py", "tests/test_metadata.py", "tests/test_backend.py"]:
        assert needle in joined_covered, f"Missing coverage summary for {needle}"

    joined_gaps = " ".join(gaps).lower()
    for needle in ["malformed pyproject.toml", "tool.packager-backend", "config_settings"]:
        assert needle in joined_gaps, f"Missing expected gap topic: {needle}"


def test_report_has_three_top_priorities() -> None:
    data = _load_report()
    priorities = data["top_priorities"]
    assert isinstance(priorities, list) and len(priorities) == 3, "top_priorities must contain exactly 3 entries."

    expected_order = [
        "packager_backend.build_backend.collect_build_request",
        "packager_backend.config.normalize_config_settings",
        "packager_backend.config.load_pyproject",
    ]
    observed = [entry["qualname"] for entry in priorities]
    assert observed == expected_order, "top_priorities should reflect the expected ranking."

    for index, entry in enumerate(priorities, start=1):
        assert entry["priority"] == index, f"Priority entry {entry['qualname']} should have rank {index}."
        for key in ["why_priority_is_high", "current_gap", "input_directions"]:
            assert key in entry, f"Top priority entry missing {key}"
        assert isinstance(entry["input_directions"], list) and entry["input_directions"], "input_directions must be a non-empty list."


if __name__ == "__main__":
    test_repository_assets_exist()
    test_report_has_required_top_level_sections()
    test_report_mentions_expected_functions_and_failures()
    test_report_summarizes_existing_tests_and_gaps()
    test_report_has_three_top_priorities()
    print("All checks passed.")
