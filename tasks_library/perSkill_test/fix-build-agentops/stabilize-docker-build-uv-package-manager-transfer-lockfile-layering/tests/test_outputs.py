from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path("/workspace/incident-digest")
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"
PLAN_PATH = REPO_ROOT / "notes" / "docker-plan.txt"
EXPECTED_OUTPUT = "digest::container-ready"
VALID_INSTRUCTIONS = {
    "ADD",
    "ARG",
    "CMD",
    "COPY",
    "ENTRYPOINT",
    "ENV",
    "EXPOSE",
    "FROM",
    "HEALTHCHECK",
    "LABEL",
    "MAINTAINER",
    "ONBUILD",
    "RUN",
    "SHELL",
    "STOPSIGNAL",
    "USER",
    "VOLUME",
    "WORKDIR",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def dockerfile_instructions() -> list[tuple[str, str, int]]:
    instructions: list[tuple[str, str, int]] = []
    pending_lines: list[str] = []
    start_line = 0

    for lineno, raw_line in enumerate(DOCKERFILE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not pending_lines:
            keyword = stripped.split(maxsplit=1)[0].upper()
            assert_true(keyword in VALID_INSTRUCTIONS, f"invalid Dockerfile instruction on line {lineno}: {stripped}")
            pending_lines = [stripped]
            start_line = lineno
        else:
            pending_lines.append(stripped)

        if stripped.endswith("\\"):
            continue

        joined = " ".join(line[:-1].strip() if line.endswith("\\") else line for line in pending_lines)
        keyword, _, body = joined.partition(" ")
        instructions.append((keyword.upper(), normalize(body), start_line))
        pending_lines = []
        start_line = 0

    assert_true(not pending_lines, "Dockerfile ends with an unfinished continued instruction")
    return instructions


def find_instruction(instructions: list[tuple[str, str, int]], keyword: str, token: str) -> int:
    target_keyword = keyword.upper()
    normalized_token = normalize(token)
    for index, (instruction_keyword, body, _) in enumerate(instructions):
        if instruction_keyword == target_keyword and normalized_token in body:
            return index
    return -1


def has_path_for_local_uv(instructions: list[tuple[str, str, int]], before_index: int) -> bool:
    for index, (keyword, body, _) in enumerate(instructions):
        if index >= before_index:
            break
        if keyword == "ENV" and "path=" in body and "/root/.local/bin" in body:
            return True
    return False


def find_uv_install_index(instructions: list[tuple[str, str, int]], before_index: int) -> int:
    for index, (keyword, body, _) in enumerate(instructions):
        if index >= before_index:
            break
        if keyword == "RUN" and "astral.sh/uv" in body and "install.sh" in body and "curl" in body:
            if has_path_for_local_uv(instructions, before_index):
                return index
    return -1


def docker_is_usable() -> bool:
    if shutil.which("docker") is None:
        return False

    result = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode == 0


def copy_sources(body: str) -> list[str]:
    parts = body.split()
    if len(parts) < 2:
        return []
    return parts[:-1]


def is_source_copy(body: str) -> bool:
    for source in copy_sources(body):
        if source in {".", "./", "app"} or source.startswith("app/") or source == "./app":
            return True
    return False


def test_plan_note() -> None:
    assert_true(PLAN_PATH.exists(), "docker plan note is missing")
    content = PLAN_PATH.read_text(encoding="utf-8").strip()
    assert_true(bool(content), "docker plan note is empty")


def test_dockerfile_structure() -> None:
    assert_true(DOCKERFILE_PATH.exists(), "Dockerfile is missing")
    instructions = dockerfile_instructions()

    install_curl = find_instruction(instructions, "RUN", "apt-get install")
    path_index = find_instruction(instructions, "ENV", "/root/.local/bin")
    copy_pyproject = find_instruction(instructions, "COPY", "pyproject.toml")
    copy_lock = find_instruction(instructions, "COPY", "uv.lock")
    copy_vendor = find_instruction(instructions, "COPY", "vendor")
    sync_index = -1
    source_copy_index = -1
    startup_entries: list[str] = []

    for index, (keyword, body, _) in enumerate(instructions):
        if keyword == "RUN" and all(token in body for token in ("uv sync", "--frozen", "--no-install-project", "--no-dev")):
            sync_index = index
        if keyword == "COPY" and is_source_copy(body):
            source_copy_index = index
        if keyword in {"CMD", "ENTRYPOINT"}:
            startup_entries.append(body)

    install_index = find_uv_install_index(instructions, sync_index if sync_index >= 0 else len(instructions))

    assert_true(install_curl >= 0, "Dockerfile must install curl before fetching the package manager installer")
    assert_true(path_index >= 0, 'Dockerfile must expose /root/.local/bin on PATH for later layers')
    assert_true(install_index >= 0, "Dockerfile must explicitly install uv inside the image before syncing dependencies")
    assert_true(copy_pyproject >= 0, "Dockerfile must copy pyproject.toml")
    assert_true(copy_lock >= 0, "Dockerfile must copy uv.lock")
    assert_true(copy_vendor >= 0, "Dockerfile must copy the vendored dependency")
    assert_true(sync_index >= 0, "Dockerfile must sync dependencies with uv using the lockfile")
    assert_true(source_copy_index >= 0, "Dockerfile must copy the application source after the dependency layer")
    assert_true(bool(startup_entries), "Dockerfile must declare how the container starts the application")
    assert_true(install_curl < install_index, "curl should be installed before running the package manager installer")
    assert_true(path_index < sync_index, "PATH should include the installed package manager before dependency sync runs")
    assert_true(install_index < sync_index, "the image must install uv before running uv sync")
    assert_true(copy_pyproject < source_copy_index, "pyproject.toml should be copied before app source")
    assert_true(copy_lock < source_copy_index, "uv.lock should be copied before app source")
    assert_true(copy_vendor < source_copy_index, "vendored dependency should be copied before app source")
    assert_true(sync_index < source_copy_index, "dependency sync should happen before copying the app")
    assert_true(find_instruction(instructions, "RUN", "uv export") == -1, "Dockerfile still exports a temporary requirements file")
    assert_true(find_instruction(instructions, "RUN", "pip install") == -1, "Dockerfile still installs dependencies with pip")
    assert_true(
        any("app/main.py" in entry or "app.main" in entry for entry in startup_entries),
        "Dockerfile must start the repository application",
    )

    for startup_entry in startup_entries:
        if startup_entry.startswith("["):
            try:
                json.loads(startup_entry)
            except json.JSONDecodeError as exc:
                raise AssertionError(f"container startup instruction is not valid JSON array syntax: {exc}") from exc


def test_local_recipe_check() -> None:
    result = subprocess.run(
        ["python3", "tools/check_recipe.py"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"recipe check failed:\n{result.stdout}")


def test_smoke_run_without_project_install() -> None:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = "/tmp/uv-cache-incident-digest-tests"
    env.pop("VIRTUAL_ENV", None)

    with tempfile.TemporaryDirectory(prefix="incident-digest-tests-") as tmpdir:
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
        if sync_result.returncode != 0:
            raise AssertionError(f"dependency sync failed:\n{sync_result.stdout}")

        shutil.copytree(REPO_ROOT / "app", tmp_root / "app")
        run_result = subprocess.run(
            ["uv", "run", "python", "app/main.py"],
            cwd=tmp_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if run_result.returncode != 0:
            raise AssertionError(f"app smoke run failed:\n{run_result.stdout}")
        assert_true(run_result.stdout.strip() == EXPECTED_OUTPUT, "unexpected app output")


def test_docker_build_and_run_when_available() -> None:
    if not docker_is_usable():
        return

    tag = f"incident-digest-task-{os.getpid()}"
    try:
        build_result = subprocess.run(
            ["docker", "build", "--tag", tag, "."],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if build_result.returncode != 0:
            raise AssertionError(f"docker build failed:\n{build_result.stdout}")

        run_result = subprocess.run(
            ["docker", "run", "--rm", tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if run_result.returncode != 0:
            raise AssertionError(f"docker run failed:\n{run_result.stdout}")
        assert_true(run_result.stdout.strip() == EXPECTED_OUTPUT, "container output did not match the expected application output")
    finally:
        subprocess.run(
            ["docker", "image", "rm", "--force", tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )


def main() -> None:
    test_plan_note()
    test_dockerfile_structure()
    test_local_recipe_check()
    test_smoke_run_without_project_install()
    test_docker_build_and_run_when_available()


if __name__ == "__main__":
    main()
