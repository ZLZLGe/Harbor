from __future__ import annotations

import os
import subprocess
from pathlib import Path


INPUT_DIR = Path(os.environ.get("MEDIA_PICK_INPUT_DIR", "/root/media_pick/input"))
OUTPUT_DIR = Path(os.environ.get("MEDIA_PICK_OUTPUT_DIR", "/root/media_pick/output"))


def file_hash_lines(root: Path) -> str:
    if not root.exists():
        return ""
    return subprocess.check_output(
        f"cd {root} && find . -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )


def test_input_files_were_not_modified() -> None:
    expected_path = Path("/opt/media-pick-input.sha256")
    if expected_path.exists():
        expected = expected_path.read_text(encoding="utf-8")
        current = file_hash_lines(INPUT_DIR)
        assert current == expected, "Input files under /root/media_pick/input were modified"


def test_no_placeholder_or_verifier_targeting_text() -> None:
    for path in [OUTPUT_DIR / "frame_index.json", OUTPUT_DIR / "delivery_report.json"]:
        text = path.read_text(encoding="utf-8").lower()
        assert "placeholder" not in text
        assert "todo" not in text
        assert "verifier" not in text
        assert "/tests" not in text


def test_output_inventory_is_clean() -> None:
    top = {path.name for path in OUTPUT_DIR.iterdir()}
    assert top == {"stills", "previews", "sheets", "frame_index.json", "delivery_report.json"}
