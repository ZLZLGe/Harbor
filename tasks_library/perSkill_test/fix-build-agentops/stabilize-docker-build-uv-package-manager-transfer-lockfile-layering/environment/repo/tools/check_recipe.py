from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"
EXPECTED_OUTPUT = "digest::container-ready"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def read_normalized_lines() -> list[str]:
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    return [" ".join(line.strip().lower().split()) for line in content.splitlines() if line.strip()]


def find_line_index(lines: list[str], token: str) -> int:
    for index, line in enumerate(lines):
        if token in line:
            return index
    return -1


def has_path_for_local_uv(lines: list[str], before_index: int) -> bool:
    for index, line in enumerate(lines):
        if index >= before_index:
            break
        if line.startswith("env ") and "path=" in line and "/root/.local/bin" in line:
            return True
    return False


def find_uv_install_index(lines: list[str], before_index: int) -> int:
    for index, line in enumerate(lines):
        if index >= before_index:
            break
        if "astral.sh/uv" in line and "install.sh" in line and "curl" in line:
            if has_path_for_local_uv(lines, before_index):
                return index
    return -1


def copy_sources(line: str) -> list[str]:
    parts = line.split()
    if len(parts) < 3:
        return []
    return parts[1:-1]


def is_source_copy(line: str) -> bool:
    for source in copy_sources(line):
        if source in {".", "./", "app"} or source.startswith("app/") or source == "./app":
            return True
    return False


def validate_dockerfile() -> None:
    lines = read_normalized_lines()

    install_curl = find_line_index(lines, "apt-get install")
    path_line = find_line_index(lines, "/root/.local/bin")
    copy_pyproject = find_line_index(lines, "copy pyproject.toml")
    copy_lock = find_line_index(lines, "uv.lock")
    copy_vendor = find_line_index(lines, "copy vendor")
    sync_line = -1
    copy_source = -1
    startup_lines: list[str] = []
    for index, line in enumerate(lines):
        if "uv sync" in line and "--frozen" in line and "--no-install-project" in line and "--no-dev" in line:
            sync_line = index
        if line.startswith("copy ") and is_source_copy(line):
            copy_source = index
        if line.startswith("cmd ") or line.startswith("entrypoint "):
            startup_lines.append(line)

    install_line = find_uv_install_index(lines, sync_line if sync_line >= 0 else len(lines))

    require(install_curl >= 0, "Dockerfile must install curl before fetching the package manager installer")
    require(path_line >= 0, "Dockerfile must expose /root/.local/bin on PATH before later uv commands")
    require(install_line >= 0, "Dockerfile must explicitly install uv inside the image before syncing dependencies")
    require(copy_pyproject >= 0, "Dockerfile must copy pyproject.toml before syncing dependencies")
    require(copy_lock >= 0, "Dockerfile must copy uv.lock before syncing dependencies")
    require(copy_vendor >= 0, "Dockerfile must copy the vendored dependency before syncing dependencies")
    require(copy_source >= 0, "Dockerfile must copy the app after the dependency layer")
    require(sync_line >= 0, "Dockerfile must use uv sync --frozen --no-install-project --no-dev")
    require(install_curl < install_line, "curl should be installed before the package manager installer runs")
    require(path_line < sync_line, "PATH should expose the installed package manager before dependency sync")
    require(install_line < sync_line, "the image must install uv before running uv sync")
    require(copy_pyproject < copy_source, "pyproject.toml should be copied before the app source")
    require(copy_lock < copy_source, "uv.lock should be copied before the app source")
    require(copy_vendor < copy_source, "vendored dependency should be copied before the app source")
    require(sync_line < copy_source, "dependency sync should happen before copying the app")
    require(find_line_index(lines, "uv export") == -1, "Dockerfile should not export a temporary requirements file")
    require(find_line_index(lines, "pip install") == -1, "Dockerfile should not install dependencies with pip")
    require(
        any("app/main.py" in line or "app.main" in line for line in startup_lines),
        "Dockerfile must start the repository application",
    )
    for line in startup_lines:
        payload = line.partition(" ")[2].strip()
        if payload.startswith("["):
            try:
                json.loads(payload)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"container startup instruction is not valid JSON array syntax: {exc}") from exc


def smoke_run() -> None:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = "/tmp/uv-cache-incident-digest"
    env.pop("VIRTUAL_ENV", None)

    with tempfile.TemporaryDirectory(prefix="incident-digest-") as tmpdir:
        tmp_root = Path(tmpdir)
        shutil.copy2(REPO_ROOT / "pyproject.toml", tmp_root / "pyproject.toml")
        shutil.copy2(REPO_ROOT / "uv.lock", tmp_root / "uv.lock")
        shutil.copytree(REPO_ROOT / "vendor", tmp_root / "vendor")

        sync_result = subprocess.run(
            ["uv", "sync", "--frozen", "--no-install-project", "--no-dev"],
            cwd=tmp_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require(sync_result.returncode == 0, f"dependency sync failed:\n{sync_result.stdout}")

        shutil.copytree(REPO_ROOT / "app", tmp_root / "app")
        run_result = subprocess.run(
            ["uv", "run", "python", "app/main.py"],
            cwd=tmp_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require(run_result.returncode == 0, f"app smoke run failed:\n{run_result.stdout}")
        require(run_result.stdout.strip() == EXPECTED_OUTPUT, f"unexpected app output: {run_result.stdout!r}")


def main() -> None:
    validate_dockerfile()
    smoke_run()


if __name__ == "__main__":
    main()
