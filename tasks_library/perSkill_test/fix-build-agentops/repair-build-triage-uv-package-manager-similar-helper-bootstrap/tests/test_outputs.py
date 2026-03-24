from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path("/opt/build-triage-helper")
FAILED_COPY = REPO_ROOT / "workspace" / "failed_copy"
HELPER_ROOT = Path("/opt/build-triage-helper-bootstrap")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_analysis_note() -> None:
    note_path = REPO_ROOT / "workspace" / "analysis" / "plan.txt"
    assert_true(note_path.exists(), "analysis note is missing")
    content = note_path.read_text(encoding="utf-8").strip()
    assert_true(bool(content), "analysis note is empty")


def test_helper_project() -> None:
    pyproject = HELPER_ROOT / "pyproject.toml"
    lockfile = HELPER_ROOT / "uv.lock"
    assert_true(pyproject.exists(), "helper pyproject.toml is missing")
    assert_true(lockfile.exists(), "helper uv.lock is missing")
    text = pyproject.read_text(encoding="utf-8").lower()
    assert_true("pyyaml" in text, "helper project does not declare pyyaml")


def test_primary_output() -> None:
    script_path = REPO_ROOT / "tools" / "fetch_patch_bundle.py"
    assert_true(script_path.exists(), "tools/fetch_patch_bundle.py is missing")
    content = script_path.read_text(encoding="utf-8")
    assert_true("unified_diff" in content, "script does not generate unified diffs")


def test_generated_patches() -> None:
    patch_dir = FAILED_COPY / "patches"
    assert_true(patch_dir.exists(), "patch directory is missing")
    patches = sorted(patch_dir.glob("bundle_patch_*.diff"))
    assert_true(len(patches) == 3, "expected exactly 3 bundle patch files")
    required_targets = {
        "workspace/failed_copy/triage_app/__init__.py",
        "workspace/failed_copy/triage_app/engine.py",
        "workspace/failed_copy/pyproject.toml",
    }
    seen_targets: set[str] = set()
    for patch_path in patches:
        content = patch_path.read_text(encoding="utf-8")
        assert_true(content.startswith("--- "), f"{patch_path.name} is not a unified diff")
        assert_true("\n+++ " in content, f"{patch_path.name} is missing the new-file header")
        for target in required_targets:
            if target in content:
                seen_targets.add(target)
    assert_true(seen_targets == required_targets, "patch files do not cover every target")


def test_repro() -> None:
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "run_repro.sh")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"reproduction failed:\n{result.stdout}")


def main() -> None:
    test_analysis_note()
    test_helper_project()
    test_primary_output()
    test_generated_patches()
    test_repro()


if __name__ == "__main__":
    main()
