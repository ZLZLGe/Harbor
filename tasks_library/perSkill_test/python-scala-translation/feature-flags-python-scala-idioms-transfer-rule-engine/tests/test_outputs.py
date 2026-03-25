#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path("/root")
USER_SCALA_FILE = ROOT / "FeatureFlagEngine.scala"
PROJECT_FIXTURE = ROOT / "scala_feature_flags"


def _load_source() -> str:
    assert USER_SCALA_FILE.exists(), "Expected /root/FeatureFlagEngine.scala to exist."
    return USER_SCALA_FILE.read_text(encoding="utf-8")


def _prepare_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "scala_feature_flags"
    shutil.copytree(
        PROJECT_FIXTURE,
        project_dir,
        ignore=shutil.ignore_patterns("target", "project/target"),
    )
    target_src = project_dir / "src" / "main" / "scala" / "featureflags"
    target_src.mkdir(parents=True, exist_ok=True)
    shutil.copy2(USER_SCALA_FILE, target_src / "FeatureFlagEngine.scala")
    return project_dir


def test_static_contract_uses_typed_adt_modeling() -> None:
    source = _load_source()

    assert "package featureflags" in source
    assert re.search(r"sealed\s+(trait|abstract\s+class)\s+AttributeValue", source)
    assert re.search(r"sealed\s+(trait|abstract\s+class)\s+Condition", source)
    assert re.search(r"class\s+FeatureFlagEngine\b", source)
    assert re.search(r"object\s+FeatureFlagEngine\b", source)
    assert re.search(r"Either\s*\[", source)
    assert re.search(r"Option\s*\[", source)
    assert re.search(r"\bmatch\s*\{", source)
    assert "stableBucket" in source
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
