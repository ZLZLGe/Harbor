#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import unittest
from pathlib import Path

APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
OUTPUT_DIR = APP_ROOT / "output"
DATA_ROOT = APP_ROOT / "data"
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/root/.codex/skills"))
INPUT_HASH_PATH = Path(os.environ.get("TASK_INPUT_HASH_PATH", "/opt/productivity-input.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("TASK_SKILL_HASH_PATH", "/opt/productivity-skill.sha256"))


def compute_hash_listing(root: Path) -> str:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = path.relative_to(root).as_posix()
        lines.append(f"{digest}  {rel}")
    return "\n".join(lines) + "\n"


class GuardrailTests(unittest.TestCase):
    def test_input_data_unchanged(self) -> None:
        baseline = INPUT_HASH_PATH.read_text(encoding="utf-8")
        current = compute_hash_listing(DATA_ROOT)
        self.assertEqual(current, baseline)

    def test_skill_unchanged_if_present(self) -> None:
        baseline = SKILL_HASH_PATH.read_text(encoding="utf-8")
        if not baseline.strip():
            try:
                skill_exists = SKILL_ROOT.exists() and any(SKILL_ROOT.rglob("*"))
            except PermissionError:
                skill_exists = False
            self.assertFalse(skill_exists)
            return
        current_root = SKILL_ROOT / "blogwatcher" if (SKILL_ROOT / "blogwatcher").is_dir() else SKILL_ROOT
        current = compute_hash_listing(current_root)
        self.assertEqual(current, baseline)

    def test_output_whitelist(self) -> None:
        files = sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_file())
        self.assertEqual(files, ["feed_digest.json", "feed_digest.md"])


if __name__ == "__main__":
    unittest.main()
