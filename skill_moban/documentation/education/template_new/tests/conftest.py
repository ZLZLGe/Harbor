from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import nbformat
import pandas as pd
import yaml
from nbclient import NotebookClient


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/app/output"))
NOTEBOOK_PATH = OUTPUT_ROOT / "student_lesson.ipynb"
GUIDE_PATH = OUTPUT_ROOT / "instructor_guide.md"
MANIFEST_PATH = OUTPUT_ROOT / "lesson_manifest.json"
SOURCE_MAP_PATH = OUTPUT_ROOT / "source_map.json"
FINAL_PACKAGE_PATH = OUTPUT_ROOT / "final_package.json"
REQUIRED_SECTION_TITLES = [
    "What we're analyzing",
    "Understand the event data",
    "Build the session funnel",
    "Compare quiz outcomes",
    "Spot metric definition traps",
    "Practice",
    "Wrap up",
]
VALID_SOURCE_FILES = {
    "lesson_brief.md",
    "learner_events.csv",
    "quiz_attempts.csv",
    "quiz_items.csv",
    "metric_definitions.yaml",
    "reference_docs/glossary.md",
    "reference_docs/facilitation_notes.md",
}


def load_notebook(path: Path = NOTEBOOK_PATH) -> nbformat.NotebookNode:
    return nbformat.read(path, as_version=4)


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_map(path: Path = SOURCE_MAP_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_final_package(path: Path = FINAL_PACKAGE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_guide_text(path: Path = GUIDE_PATH) -> str:
    return path.read_text(encoding="utf-8")


def extract_headings(nb: nbformat.NotebookNode) -> list[str]:
    headings: list[str] = []
    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        for line in cell.source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(stripped.lstrip("#").strip())
    return headings


def find_required_heading_positions(headings: list[str]) -> list[int]:
    positions: list[int] = []
    for title in REQUIRED_SECTION_TITLES:
        try:
            positions.append(headings.index(title))
        except ValueError:
            positions.append(-1)
    return positions


def execute_notebook(path: Path = NOTEBOOK_PATH) -> nbformat.NotebookNode:
    nb = load_notebook(path)
    client = NotebookClient(nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(OUTPUT_ROOT)}})
    client.execute()
    return nb


def markdown_section_text(nb: nbformat.NotebookNode, title: str) -> str:
    parts: list[str] = []
    in_section = False

    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue

        headings = [line.strip().lstrip("#").strip() for line in cell.source.splitlines() if line.strip().startswith("#")]
        if title in headings:
            in_section = True
            parts.append(cell.source)
            continue

        if in_section and headings:
            break

        if in_section:
            parts.append(cell.source)

    return "\n".join(parts)


def run_build() -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    build_script = WORKSPACE_ROOT / "build_lesson_package.py"
    completed = subprocess.run(
        [sys.executable, str(build_script)],
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    payload: dict[str, Any] = {}
    if FINAL_PACKAGE_PATH.exists():
        payload = load_final_package()
    return completed, payload


def cell_output_text(cell: nbformat.NotebookNode) -> str:
    parts: list[str] = []
    for output in cell.get("outputs", []):
        if "text" in output:
            text = output["text"]
            if isinstance(text, list):
                parts.extend(text)
            else:
                parts.append(text)
        data = output.get("data", {})
        for key in ("text/plain", "text/html"):
            value = data.get(key)
            if isinstance(value, list):
                parts.extend(value)
            elif isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


def substantive_output_cells(nb: nbformat.NotebookNode) -> list[nbformat.NotebookNode]:
    cells: list[nbformat.NotebookNode] = []
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        text = cell_output_text(cell).strip()
        has_image = any("image/png" in output.get("data", {}) for output in cell.get("outputs", []))
        if has_image or len(text) >= 20:
            cells.append(cell)
    return cells


def load_metric_definitions() -> dict[str, Any]:
    return yaml.safe_load((WORKSPACE_ROOT / "metric_definitions.yaml").read_text(encoding="utf-8"))


def compute_reference_metrics() -> dict[str, float]:
    events = pd.read_csv(WORKSPACE_ROOT / "learner_events.csv")
    attempts = pd.read_csv(WORKSPACE_ROOT / "quiz_attempts.csv")
    quiz_items = pd.read_csv(WORKSPACE_ROOT / "quiz_items.csv")

    started = events.loc[events["event_name"] == "session_started", "learner_id"].nunique()
    completed = events.loc[events["event_name"] == "lesson_completed", "learner_id"].nunique()
    practice_opened = events.loc[events["event_name"] == "practice_opened", "learner_id"].nunique()
    practice_submitted = events.loc[
        events["event_name"] == "practice_submitted", "learner_id"
    ].nunique()
    attempted = attempts["learner_id"].nunique()
    passed_any = attempts.loc[attempts["passed"] == 1, "learner_id"].nunique()
    retry_learners = attempts.loc[attempts["attempt_number"] > 1, "learner_id"].nunique()

    return {
        "started": float(started),
        "completed": float(completed),
        "practice_opened": float(practice_opened),
        "practice_submitted": float(practice_submitted),
        "completion_rate": round(completed / started, 4),
        "practice_submission_rate": round(practice_submitted / practice_opened, 4),
        "quiz_pass_rate": round(passed_any / attempted, 4),
        "retry_rate": round(retry_learners / attempted, 4),
        "top_misconception_topic": str(
            quiz_items.assign(
                error_rate=quiz_items["incorrect_learners"]
                / (quiz_items["correct_learners"] + quiz_items["incorrect_learners"])
            )
            .sort_values("error_rate", ascending=False)
            .iloc[0]["topic"]
        ),
    }


def accepted_metric_formats(value: float) -> set[str]:
    percent = round(value * 100, 2)
    return {
        f"{value}",
        f"{value:.2f}",
        f"{percent:.0f}%",
        f"{percent:.1f}%",
        f"{percent:.2f}%",
    }
