from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path("/workspace/dev-bootstrap-station")
SCRIPT_PATH = REPO_ROOT / "scripts" / "bootstrap_env.sh"
PLAN_PATH = REPO_ROOT / "notes" / "bootstrap-plan.txt"
REPORT_PATH = REPO_ROOT / "var" / "bootstrap_report.txt"
EXPECTED_REPORT = "\n".join(
    [
        "project=dev-bootstrap-station",
        "owner=platform-docs",
        "commands=collect -> preview -> serve",
        "status=bootstrap-ready",
        "",
    ]
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def uv_env() -> dict[str, str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = "/tmp/uv-cache-dev-bootstrap-tests"
    env["UV_PYTHON_INSTALL_DIR"] = "/tmp/uv-python-dev-bootstrap-tests"
    env.pop("VIRTUAL_ENV", None)
    return env


def test_plan_note() -> None:
    assert_true(PLAN_PATH.exists(), "bootstrap plan note is missing")
    content = PLAN_PATH.read_text(encoding="utf-8").strip()
    assert_true(bool(content), "bootstrap plan note is empty")


def test_script_content() -> None:
    assert_true(SCRIPT_PATH.exists(), "bootstrap script is missing")
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    required_tokens = [
        ".python-version",
        "uv venv .venv --python",
        'uv run --python "$PYTHON_VERSION" python -m devbootstrap.cli',
        "--output var/bootstrap_report.txt",
    ]
    for token in required_tokens:
        assert_true(token in script, f"bootstrap script is missing `{token}`")

    forbidden_tokens = [
        "python3.10 -m venv",
        "pip install",
        ".venv/bin/activate",
        "dev-bootstrap --seed",
    ]
    for token in forbidden_tokens:
        assert_true(token not in script, f"bootstrap script still contains `{token}`")


def test_bootstrap_execution() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env=uv_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"bootstrap script failed:\n{result.stdout}")

    assert_true((REPO_ROOT / ".venv" / "pyvenv.cfg").exists(), "virtual environment was not created")
    assert_true(REPORT_PATH.exists(), "bootstrap report is missing")
    content = REPORT_PATH.read_text(encoding="utf-8")
    assert_true(content == EXPECTED_REPORT, "bootstrap report content is incorrect")


def test_local_check() -> None:
    result = subprocess.run(
        ["python", "tools/check_bootstrap.py"],
        cwd=REPO_ROOT,
        env=uv_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"bootstrap checker failed:\n{result.stdout}")


def main() -> None:
    test_plan_note()
    test_script_content()
    test_bootstrap_execution()
    test_local_check()


if __name__ == "__main__":
    main()
