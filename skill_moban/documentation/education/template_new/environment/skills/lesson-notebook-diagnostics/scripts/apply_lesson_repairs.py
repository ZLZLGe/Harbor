from __future__ import annotations

import os
import shutil
from pathlib import Path
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = SKILL_ROOT / "data"
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/app/output"))
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "student_lesson.ipynb",
        "instructor_guide.md",
        "lesson_manifest.json",
        "source_map.json",
    ]:
        shutil.copy2(DATA_ROOT / name, OUTPUT_ROOT / name)

    completed = subprocess.run(
        [sys.executable, str(WORKSPACE_ROOT / "build_lesson_package.py")],
        check=False,
        text=True,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
