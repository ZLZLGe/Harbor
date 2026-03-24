from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "bootstrap_env.sh"
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    require(SCRIPT_PATH.exists(), "bootstrap script is missing")
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    required_tokens = [
        ".python-version",
        "uv venv",
        "uv run --python",
        "python -m devbootstrap.cli",
    ]
    for token in required_tokens:
        require(token in script, f"bootstrap script is missing `{token}`")

    forbidden_tokens = [
        "python3.10 -m venv",
        "pip install",
        ".venv/bin/activate",
        "dev-bootstrap --seed",
    ]
    for token in forbidden_tokens:
        require(token not in script, f"bootstrap script still contains `{token}`")

    require((REPO_ROOT / ".venv" / "pyvenv.cfg").exists(), "virtual environment was not created")
    require(REPORT_PATH.exists(), "bootstrap report is missing")
    content = REPORT_PATH.read_text(encoding="utf-8")
    require(content == EXPECTED_REPORT, "bootstrap report content is incorrect")
    print("bootstrap check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
