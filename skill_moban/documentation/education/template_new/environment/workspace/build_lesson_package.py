from __future__ import annotations

import json
import os
from pathlib import Path

import nbformat
import yaml


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
OUTPUT = Path(os.environ.get("OUTPUT_ROOT", "/app/output"))
REQUIRED = [
    "What we're analyzing",
    "Understand the event data",
    "Build the session funnel",
    "Compare quiz outcomes",
    "Spot metric definition traps",
    "Practice",
    "Wrap up",
]
VALID_SOURCES = {
    "lesson_brief.md",
    "learner_events.csv",
    "quiz_attempts.csv",
    "quiz_items.csv",
    "metric_definitions.yaml",
    "reference_docs/glossary.md",
    "reference_docs/facilitation_notes.md",
}


def extract_headings_from_notebook(path: Path) -> list[str]:
    notebook = nbformat.read(path, as_version=4)
    headings: list[str] = []
    for cell in notebook.cells:
        if cell.cell_type != "markdown":
            continue
        for line in cell.source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(stripped.lstrip("#").strip())
    return headings


def extract_headings_from_markdown(path: Path) -> list[str]:
    headings: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
    return headings


def main() -> int:
    notebook_path = OUTPUT / "student_lesson.ipynb"
    guide_path = OUTPUT / "instructor_guide.md"
    manifest_path = OUTPUT / "lesson_manifest.json"
    source_map_path = OUTPUT / "source_map.json"
    final_package_path = OUTPUT / "final_package.json"

    for path in [notebook_path, guide_path, manifest_path, source_map_path]:
        if not path.exists():
            raise SystemExit(f"Missing output: {path}")

    notebook_headings = extract_headings_from_notebook(notebook_path)
    guide_headings = extract_headings_from_markdown(guide_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    metric_definitions = yaml.safe_load((WORKSPACE / "metric_definitions.yaml").read_text(encoding="utf-8"))
    valid_metric_names = {item["name"] for item in metric_definitions["metrics"]}

    if [section["title"] for section in manifest["sections"]] != REQUIRED:
        raise SystemExit("Manifest section order mismatch")
    if [section["title"] for section in source_map["sections"]] != REQUIRED:
        raise SystemExit("Source map section order mismatch")
    if REQUIRED != [heading for heading in notebook_headings if heading in REQUIRED]:
        raise SystemExit("Notebook section order mismatch")
    if REQUIRED != [heading for heading in guide_headings if heading in REQUIRED]:
        raise SystemExit("Guide section order mismatch")

    for section in manifest["sections"]:
        if not set(section["uses_files"]).issubset(VALID_SOURCES):
            raise SystemExit(f"Manifest uses invalid source file: {section}")
    for section in source_map["sections"]:
        if not set(section["sources"]).issubset(VALID_SOURCES):
            raise SystemExit(f"Source map uses invalid source file: {section}")
        for claim in section["claims"]:
            if not set(claim["source_files"]).issubset(VALID_SOURCES):
                raise SystemExit(f"Claim uses invalid source file: {claim}")

    for metric in manifest["key_metrics"]:
        if metric["name"] not in valid_metric_names:
            raise SystemExit(f"Invalid metric name: {metric['name']}")

    final_package = {
        "validation_passed": True,
        "notebook_file": str(notebook_path),
        "guide_file": str(guide_path),
        "manifest_file": str(manifest_path),
        "source_map_file": str(source_map_path),
        "section_count": len(REQUIRED),
        "claim_count": sum(len(section["claims"]) for section in source_map["sections"]),
        "metric_count": len(manifest["key_metrics"]),
    }
    final_package_path.write_text(json.dumps(final_package, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
