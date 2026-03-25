#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path("/root")
USER_SCALA_FILE = ROOT / "CsvNormalizer.scala"
PROJECT_FIXTURE = ROOT / "scala_normalizer"


def _load_source() -> str:
    assert USER_SCALA_FILE.exists(), "Expected /root/CsvNormalizer.scala to exist."
    return USER_SCALA_FILE.read_text(encoding="utf-8")


def _prepare_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "scala_normalizer"
    shutil.copytree(
        PROJECT_FIXTURE,
        project_dir,
        ignore=shutil.ignore_patterns("target", "project/target"),
    )
    target_src = project_dir / "src" / "main" / "scala" / "csvnormalizer"
    target_src.mkdir(parents=True, exist_ok=True)
    shutil.copy2(USER_SCALA_FILE, target_src / "CsvNormalizer.scala")
    return project_dir


def test_static_contract_mentions_idiomatic_optional_modeling() -> None:
    source = _load_source()

    assert "package csvnormalizer" in source
    assert re.search(r"sealed\s+(trait|abstract\s+class)\s+NormalizedValue", source)
    assert re.search(r"class\s+CsvNormalizer\b", source)
    assert re.search(r"object\s+CsvNormalizer\b", source)
    assert re.search(r"Option\s*\[", source)
    assert re.search(r"\bnull\b", source) is None


def test_scala_behavior_suite_passes(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    result = subprocess.run(
        ["sbt", "-batch", "test"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=360,
        check=False,
    )

    output = result.stdout + "\n" + result.stderr
    assert result.returncode == 0, output
