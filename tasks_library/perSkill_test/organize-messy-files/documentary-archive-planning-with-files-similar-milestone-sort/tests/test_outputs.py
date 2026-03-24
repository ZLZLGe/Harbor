import json
import os
from pathlib import Path

TASK_ROOT = Path(os.environ.get("ARCHIVE_TASK_ROOT", "/root"))
ARCHIVE_ROOT = TASK_ROOT / "documentary_archive"
INBOX = ARCHIVE_ROOT / "inbox"
MANIFEST_PATH = TASK_ROOT / "reports" / "archive_manifest.json"

EXPECTED = {
    "01_development": [
        "aurora_packet_01.pdf",
        "delta_notes.docx",
        "horizon_overview.pptx",
        "table_read_excerpt.txt",
    ],
    "02_pre_production": [
        "harbor_packet_02.pdf",
        "matrix_sheet.xlsx",
        "route_sync_excerpt.txt",
        "window_notes.docx",
    ],
    "03_production": [
        "card_index.xlsx",
        "field_packet_03.pdf",
        "night_shift_excerpt.txt",
        "release_notes.docx",
    ],
    "04_post_production": [
        "assembly_excerpt.txt",
        "bench_packet_04.pdf",
        "lane_notes.docx",
        "mix_sheet.xlsx",
    ],
    "05_festival_delivery": [
        "launch_packet_05.pdf",
        "path_overview.pptx",
        "press_notes.docx",
        "qc_sheet.xlsx",
    ],
    "06_finance_and_admin": [
        "cash_sheet.xlsx",
        "closeout_notes.docx",
        "partner_overview.pptx",
        "vendor_packet_06.pdf",
    ],
}

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".pptx", ".txt", ".xlsx"}


def test_expected_archive_layout():
    assert ARCHIVE_ROOT.is_dir(), "Archive root is missing."
    assert INBOX.is_dir(), "Inbox folder is missing."

    for folder, expected_files in EXPECTED.items():
        folder_path = ARCHIVE_ROOT / folder
        assert folder_path.is_dir(), f"Missing milestone folder: {folder}"
        actual_files = sorted(path.name for path in folder_path.iterdir() if path.is_file())
        assert actual_files == expected_files


def test_inbox_is_cleared():
    leftovers = sorted(
        str(path.relative_to(INBOX))
        for path in INBOX.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    assert leftovers == []


def test_manifest_matches_archive():
    assert MANIFEST_PATH.is_file(), "archive_manifest.json is missing."
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["archive_root"] == str(ARCHIVE_ROOT)
    assert manifest["inbox_cleared"] is True
    assert manifest["total_files"] == 24

    milestones = manifest["milestones"]
    assert [entry["folder"] for entry in milestones] == sorted(EXPECTED)

    total_from_manifest = 0
    for entry in milestones:
        folder = entry["folder"]
        expected_files = EXPECTED[folder]
        assert isinstance(entry["scope"], str)
        assert len(entry["scope"].strip()) >= 20
        assert entry["files"] == expected_files
        assert entry["file_count"] == len(expected_files)

        folder_path = ARCHIVE_ROOT / folder
        actual_files = sorted(path.name for path in folder_path.iterdir() if path.is_file())
        assert actual_files == entry["files"]
        total_from_manifest += entry["file_count"]

    assert total_from_manifest == manifest["total_files"]


def test_working_notes_exist():
    required_notes = [
        TASK_ROOT / "task_plan.md",
        TASK_ROOT / "findings.md",
        TASK_ROOT / "progress.md",
    ]
    for note_path in required_notes:
        assert note_path.is_file(), f"Missing working note: {note_path.name}"
        text = note_path.read_text(encoding="utf-8").strip()
        assert len(text) >= 40, f"Working note is too short: {note_path.name}"

    task_plan = (TASK_ROOT / "task_plan.md").read_text(encoding="utf-8")
    findings = (TASK_ROOT / "findings.md").read_text(encoding="utf-8")
    progress = (TASK_ROOT / "progress.md").read_text(encoding="utf-8")

    assert "01_development" in task_plan
    assert "06_finance_and_admin" in task_plan
    assert "02_pre_production" in findings
    assert "05_festival_delivery" in findings
    assert "archive_manifest.json" in progress
