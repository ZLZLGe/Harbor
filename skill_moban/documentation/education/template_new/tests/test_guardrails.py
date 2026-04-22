from __future__ import annotations

import os
from pathlib import Path

from conftest import (
    FINAL_PACKAGE_PATH,
    GUIDE_PATH,
    MANIFEST_PATH,
    NOTEBOOK_PATH,
    SOURCE_MAP_PATH,
    VALID_SOURCE_FILES,
    load_guide_text,
    load_manifest,
    load_notebook,
    load_source_map,
)


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))


def test_protected_inputs_exist_and_are_nontrivial() -> None:
    for relative in [
        "lesson_brief.md",
        "learner_events.csv",
        "quiz_attempts.csv",
        "quiz_items.csv",
        "metric_definitions.yaml",
        "draft_notebook.ipynb",
        "draft_instructor_guide.md",
        "build_lesson_package.py",
        "reference_docs/glossary.md",
        "reference_docs/facilitation_notes.md",
    ]:
        path = WORKSPACE_ROOT / relative
        assert path.exists(), path
        assert path.stat().st_size > 40, path


def test_outputs_are_not_placeholders() -> None:
    notebook = load_notebook()
    guide = load_guide_text().lower()
    manifest = load_manifest()
    source_map = load_source_map()

    markdown_cells = [cell for cell in notebook.cells if cell.cell_type == "markdown"]
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert len(markdown_cells) >= 7
    assert len(code_cells) >= 6
    assert NOTEBOOK_PATH.stat().st_size > 5000
    assert GUIDE_PATH.stat().st_size > 1200
    assert MANIFEST_PATH.stat().st_size > 500
    assert SOURCE_MAP_PATH.stat().st_size > 800

    blocked = {"todo", "placeholder", "tbd", "lorem ipsum"}
    blob = "\n".join(cell.source for cell in notebook.cells).lower()
    for token in blocked:
        assert token not in blob
        assert token not in guide

    assert manifest["lesson_info"]["audience"] == "new data analysts"
    assert len(source_map["sections"]) == 7


def test_bundle_references_only_visible_sources() -> None:
    manifest = load_manifest()
    source_map = load_source_map()

    for section in manifest["sections"]:
        assert set(section["uses_files"]).issubset(VALID_SOURCE_FILES)
    if "source_files" in manifest:
        assert set(manifest["source_files"]).issubset(VALID_SOURCE_FILES)
    for section in source_map["sections"]:
        assert set(section["sources"]).issubset(VALID_SOURCE_FILES)
        for claim in section["claims"]:
            assert set(claim["source_files"]).issubset(VALID_SOURCE_FILES)


def test_final_package_is_real_build_output() -> None:
    assert FINAL_PACKAGE_PATH.exists()
    payload = FINAL_PACKAGE_PATH.read_text(encoding="utf-8").lower()
    assert "validation_passed" in payload
    assert "guide_file" in payload
    assert "source_map_file" in payload
