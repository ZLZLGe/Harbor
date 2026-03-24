from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path("/workspace/scoreboard-service")
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "python-ci.yml"
PLAN_PATH = REPO_ROOT / "ci-notes" / "plan.txt"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_plan_note() -> None:
    assert_true(PLAN_PATH.exists(), "plan note is missing")
    content = PLAN_PATH.read_text(encoding="utf-8").strip()
    assert_true(bool(content), "plan note is empty")


def test_workflow_content() -> None:
    assert_true(WORKFLOW_PATH.exists(), "workflow file is missing")
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert_true("actions/setup-python@v5" in workflow, "workflow must keep setup-python@v5")
    assert_true('python-version: "3.11"' in workflow, "workflow must pin Python 3.11")
    assert_true("uv sync --locked" in workflow, "workflow must use uv sync --locked")
    assert_true(
        "uv run python -m unittest discover -s tests -q" in workflow,
        "workflow must run unittest through uv",
    )
    assert_true("requirements.txt" not in workflow, "workflow still references requirements.txt")
    assert_true("pip install -r" not in workflow, "workflow still installs dependencies with pip")


def test_local_ci_check() -> None:
    result = subprocess.run(
        ["python", "scripts/local_ci_check.py"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"local ci check failed:\n{result.stdout}")


def main() -> None:
    test_plan_note()
    test_workflow_content()
    test_local_ci_check()


if __name__ == "__main__":
    main()
