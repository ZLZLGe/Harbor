#!/usr/bin/env python3

import re
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_PATTERNS = {
    "AuditEvent": r"case\s+class\s+AuditEvent",
    "EventSummary": r"case\s+class\s+EventSummary",
    "EventNormalizer": r"class\s+EventNormalizer",
    "parseLine": r"def\s+parseLine\s*\(",
    "normalizeTimestamp": r"def\s+normalizeTimestamp\s*\(",
    "extractLabels": r"def\s+extractLabels\s*\(",
    "normalizeEvent": r"def\s+normalizeEvent\s*\(",
    "loadEvents": r"def\s+loadEvents\s*\(",
    "summarize": r"def\s+summarize\s*\(",
    "normalizeFile": r"def\s+normalizeFile\s*\(",
    "loadAndSummarize": r"def\s+loadAndSummarize\s*\(",
}


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    if len(sys.argv) != 3:
        return fail("usage: test_outputs.py <scala-file> <project-dir>")

    scala_file = Path(sys.argv[1])
    project_dir = Path(sys.argv[2])

    if not scala_file.is_file():
        return fail(f"missing Scala file: {scala_file}")

    source = scala_file.read_text(encoding="utf-8")
    missing = [name for name, pattern in REQUIRED_PATTERNS.items() if re.search(pattern, source) is None]
    if missing:
        return fail("missing required Scala declarations: " + ", ".join(missing))

    target_file = project_dir / "src" / "main" / "scala" / "eventnormalizer" / "EventNormalizer.scala"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if scala_file.resolve() != target_file.resolve():
        shutil.copy(scala_file, target_file)

    proc = subprocess.run(
        ["sbt", "test"],
        cwd=project_dir,
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )

    combined_output = proc.stdout + proc.stderr
    print(combined_output)

    if proc.returncode != 0:
        return fail("sbt test failed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
