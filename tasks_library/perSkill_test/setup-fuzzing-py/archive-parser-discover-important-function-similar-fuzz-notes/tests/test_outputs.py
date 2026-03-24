from __future__ import annotations

import os
from pathlib import Path


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
REPORT_PATH = APP_DIR / "archive_fuzz_targets.md"
REPO_PATH = APP_DIR / "archivekit_repo"


def _read_report() -> str:
    assert REPORT_PATH.exists(), "archive_fuzz_targets.md does not exist."
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert len(text.strip()) > 800, "archive_fuzz_targets.md is too short to be a real analysis."
    return text


def _contains_any(text: str, options: list[str]) -> bool:
    lowered = text.lower()
    return any(option.lower() in lowered for option in options)


def test_repository_assets_exist() -> None:
    assert REPO_PATH.exists(), "archivekit_repo is missing."
    assert (REPO_PATH / "archivekit" / "headers.py").exists(), "headers.py is missing."
    assert (REPO_PATH / "tests" / "test_reader.py").exists(), "test_reader.py is missing."


def test_report_mentions_key_files_and_functions() -> None:
    text = _read_report()

    for needle in ["headers.py", "metadata.py", "reader.py"]:
        assert needle in text, f"Expected important file mention: {needle}"

    for needle in [
        "parse_header_block",
        "parse_extended_headers",
        "iter_entries",
        "_parse_numeric_field",
    ]:
        assert needle in text, f"Expected important function mention: {needle}"


def test_report_references_existing_tests_and_gaps() -> None:
    text = _read_report()

    for needle in ["tests/test_headers.py", "tests/test_reader.py", "tests/test_filters.py"]:
        assert needle in text, f"Expected test coverage summary mention: {needle}"

    gap_topics = [
        ["truncated", "截断"],
        ["checksum", "校验和"],
        ["pax", "extended header"],
        ["utf-8", "unicode"],
    ]
    for topic_group in gap_topics:
        assert _contains_any(text, topic_group), f"Expected a gap discussion for: {topic_group}"


def test_report_has_final_shortlist_with_expected_targets() -> None:
    text = _read_report()

    assert _contains_any(text, ["final shortlist", "shortlist", "最终"]), "Missing final shortlist section."
    for needle in [
        "archivekit.headers.parse_header_block",
        "archivekit.metadata.parse_extended_headers",
        "archivekit.reader.ArchiveReader.iter_entries",
    ]:
        assert needle in text, f"Expected shortlisted target: {needle}"

    for needle in ["seed", "priority", "missing coverage"]:
        assert _contains_any(text, [needle, "优先级", "缺口"]), f"Expected shortlist rationale keyword: {needle}"


if __name__ == "__main__":
    test_repository_assets_exist()
    test_report_mentions_key_files_and_functions()
    test_report_references_existing_tests_and_gaps()
    test_report_has_final_shortlist_with_expected_targets()
    print("All checks passed.")
