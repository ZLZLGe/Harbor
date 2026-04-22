from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest
import requests


BASE_URL = os.environ.get("CONTROL_PLANE_URL", "http://127.0.0.1:8300")
EXPECTED_SNAPSHOT_ID = "mirror-2026-04-18-01"
MIRROR_URL = os.environ.get("MIRROR_API_URL", "http://127.0.0.1:8320")
CONTROL_PLANE_SERVER_PATH = os.environ.get("CONTROL_PLANE_SERVER_PATH", "/services/control-plane/server.py")
MIRROR_SERVER_PATH = os.environ.get("MIRROR_SERVER_PATH", "/services/mirror-service/server.py")
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
DEPLOYMENT_TEMPLATE_PATH = os.environ.get(
    "DEPLOYMENT_TEMPLATE_PATH",
    f"{WORKSPACE_ROOT}/infra/containerapp.template.json",
)


def _wait_for_http(url: str, *, timeout_sec: float) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code < 500:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.25)
    return False


def _spawn_if_needed(url: str, cmd: list[str], env: dict[str, str], *, timeout_sec: float) -> None:
    if _wait_for_http(url, timeout_sec=1):
        return

    subprocess.Popen(  # noqa: S603
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    if not _wait_for_http(url, timeout_sec=timeout_sec):
        raise RuntimeError(f"failed to start service for {url}")


@pytest.fixture(scope="session", autouse=True)
def ensure_hidden_runtime() -> None:
    mirror_env = os.environ.copy()
    mirror_env.setdefault("MIRROR_DATA_PATH", os.environ.get("MIRROR_DATA_PATH", "/services/mirror-service/data/incidents_snapshot.json"))
    mirror_env.setdefault("MIRROR_AUDIT_PATH", os.environ.get("MIRROR_AUDIT_PATH", "/tmp/mirror_audit_log.json"))
    _spawn_if_needed(
        f"{MIRROR_URL}/health",
        [sys.executable, MIRROR_SERVER_PATH],
        mirror_env,
        timeout_sec=20,
    )

    control_env = os.environ.copy()
    control_env.setdefault("WORKSPACE_ROOT", WORKSPACE_ROOT)
    control_env.setdefault("DEPLOYMENT_TEMPLATE_PATH", DEPLOYMENT_TEMPLATE_PATH)
    control_env.setdefault("MIRROR_API_URL", MIRROR_URL)
    _spawn_if_needed(
        f"{BASE_URL}/__control/status",
        [sys.executable, CONTROL_PLANE_SERVER_PATH],
        control_env,
        timeout_sec=20,
    )


def control_post(path: str) -> requests.Response:
    response = requests.post(f"{BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response


def control_get(path: str) -> requests.Response:
    response = requests.get(f"{BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response


def public_get(path: str) -> requests.Response:
    return requests.get(f"{BASE_URL}{path}", timeout=10)


def reset_and_apply() -> dict:
    control_post("/__control/reset")
    response = control_post("/__control/apply")
    return response.json()["status"]


def mirror_audit() -> dict:
    return control_get("/__control/mirror-audit").json()
