import json
from pathlib import Path

CONFIG = json.loads(Path("/root/data/expected_layout.json").read_text())
TARGET_ROOT = Path("/root/library")
SOURCE_ROOT = Path("/root/inbox")
REPORT_PATH = Path("/root/similar_sort_report.json")


def test_report_exists_and_shape():
    assert REPORT_PATH.exists(), "Missing /root/similar_sort_report.json"
    report = json.loads(REPORT_PATH.read_text())
    assert set(report.keys()) == {"total_files", "moved_files", "folders"}
    assert report["total_files"] == sum(len(v) for v in CONFIG.values())
    assert report["moved_files"] == report["total_files"]
    assert report["folders"] == {k: len(v) for k, v in CONFIG.items()}


def test_files_are_in_expected_folders_only():
    expected_files = set()
    for folder, files in CONFIG.items():
        folder_path = TARGET_ROOT / folder
        assert folder_path.is_dir(), f"Missing folder {folder_path}"
        for name in files:
            assert (folder_path / name).is_file(), f"Missing {name} in {folder}"
            expected_files.add(name)

    leftovers = [p.name for p in SOURCE_ROOT.glob("*") if p.is_file() and p.name in expected_files]
    assert not leftovers, f"Leftover files in inbox: {leftovers}"
