import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import requests


WORKSPACE = Path(os.getenv("WORKSPACE", "/workspace"))
REPO_DIR = WORKSPACE / "admin-import-service"
PATCH_FILE = WORKSPACE / "patches" / "0001-admin-import-type-whitelist.patch"
PRISTINE_REPO = Path("/opt/task-assets/admin-import-service-pristine")
SERVICE_PORT = 18081


def load_json_asset(name: str):
  with (WORKSPACE / "import-packages" / name).open() as handle:
    return json.load(handle)


def wait_for_port(port: int, timeout: float = 20.0):
  deadline = time.time() + timeout
  while time.time() < deadline:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
      sock.settimeout(0.5)
      if sock.connect_ex(("127.0.0.1", port)) == 0:
        return
    time.sleep(0.2)
  raise AssertionError(f"admin import service did not start on port {port}")


def build_service():
  subprocess.run(
      ["mvn", "-q", "-DskipTests", "package", "dependency:copy-dependencies"],
      cwd=REPO_DIR,
      check=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      timeout=180,
  )


def start_service():
  env = os.environ.copy()
  env["ADMIN_IMPORT_PORT"] = str(SERVICE_PORT)
  process = subprocess.Popen(
      [
          "java",
          "-cp",
          "target/classes:target/dependency/*",
          "com.harbor.adminimport.AdminImportApplication",
      ],
      cwd=REPO_DIR,
      env=env,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
  )
  wait_for_port(SERVICE_PORT)
  return process


def stop_process(process):
  process.terminate()
  try:
    process.wait(timeout=10)
  except subprocess.TimeoutExpired:
    process.kill()
    process.wait(timeout=5)


def test_patch_file_exists():
  assert PATCH_FILE.exists(), "missing required patch file"
  assert PATCH_FILE.stat().st_size > 0, "patch file is empty"


def test_patch_applies_cleanly_to_pristine_source():
  with tempfile.TemporaryDirectory() as tmpdir:
    temp_repo = Path(tmpdir) / "admin-import-service"
    shutil.copytree(PRISTINE_REPO, temp_repo)
    subprocess.run(
        ["git", "apply", "--check", str(PATCH_FILE)],
        cwd=temp_repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )


def test_working_tree_was_modified():
  pristine_sources = {
      path.relative_to(PRISTINE_REPO).as_posix(): path.read_text()
      for path in PRISTINE_REPO.rglob("*.java")
  }
  current_sources = {
      path.relative_to(REPO_DIR).as_posix(): path.read_text()
      for path in REPO_DIR.rglob("*.java")
  }
  assert current_sources != pristine_sources, "admin-import-service does not contain applied source changes"


def test_admin_import_behavior():
  build_service()
  process = start_service()
  try:
    base_url = f"http://127.0.0.1:{SERVICE_PORT}/admin/imports"

    theme_only = requests.post(base_url, json=load_json_asset("theme-only.json"), timeout=10)
    assert theme_only.status_code == 200, theme_only.text
    theme_payload = theme_only.json()
    assert theme_payload["batchId"] == "theme-batch-2026-03"
    assert theme_payload["importedCount"] == 1
    assert theme_payload["importedKinds"] == ["theme"]

    mixed = requests.post(base_url, json=load_json_asset("theme-and-dashboard.json"), timeout=10)
    assert mixed.status_code == 200, mixed.text
    mixed_payload = mixed.json()
    assert mixed_payload["batchId"] == "release-batch-17"
    assert mixed_payload["importedCount"] == 2
    assert set(mixed_payload["importedKinds"]) == {"theme", "dashboard"}

    exploit_payload = load_json_asset("exploit-dangerous-import.json")
    artifact_path = str(Path("/tmp") / f"admin-import-marker-{uuid.uuid4().hex}.txt")
    exploit_payload["operations"][0]["artifactPath"] = artifact_path

    exploit = requests.post(base_url, json=exploit_payload, timeout=10)
    assert 400 <= exploit.status_code < 500, exploit.text
    assert "error" in exploit.json()
    assert not Path(artifact_path).exists(), "dangerous import was instantiated during deserialization"
  finally:
    stop_process(process)
