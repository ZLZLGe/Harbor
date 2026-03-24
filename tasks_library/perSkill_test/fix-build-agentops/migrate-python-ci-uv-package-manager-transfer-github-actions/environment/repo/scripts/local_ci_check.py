from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "python-ci.yml"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert_true("actions/setup-python" in workflow, "workflow must keep setup-python")
    assert_true("uv sync --locked" in workflow, "workflow must sync from the lockfile")
    assert_true("uv run python -m unittest" in workflow, "workflow must run tests through uv")
    assert_true("requirements.txt" not in workflow, "workflow still references requirements.txt")
    assert_true("pip install -r" not in workflow, "workflow still installs with pip requirements")

    subprocess.run(
        ["uv", "sync", "--locked"],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        ["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=REPO_ROOT,
        check=True,
    )
    print("local ci check passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
